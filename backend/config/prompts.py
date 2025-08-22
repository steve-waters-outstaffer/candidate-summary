import os
import json
import logging

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')

def get_available_prompts():
    """Scans the prompts directory and returns a list of available prompt configurations."""
    prompts = []
    if not os.path.exists(PROMPTS_DIR):
        logging.error(f"Prompts directory not found at: {PROMPTS_DIR}")
        return prompts

    for root, dirs, files in os.walk(PROMPTS_DIR):
        for file in files:
            if file.endswith('.json'):
                try:
                    relative_path = os.path.relpath(os.path.join(root, file), PROMPTS_DIR)
                    prompt_id = os.path.splitext(relative_path.replace(os.path.sep, '.'))[0]
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        prompts.append({
                            'id': prompt_id,
                            'name': data.get('name', prompt_id)
                        })
                except Exception as e:
                    logging.error(f"Error loading prompt {file}: {e}")
    return sorted(prompts, key=lambda p: p['name'])

def get_prompt(prompt_type="recruitment.detailed"):
    """Retrieve a specific prompt configuration from its JSON file."""
    file_path = os.path.join(PROMPTS_DIR, *prompt_type.split('.')) + '.json'
    if not os.path.exists(file_path):
        raise ValueError(f"Prompt type '{prompt_type}' not found at {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading or parsing prompt file {file_path}: {e}")
        raise

def build_full_prompt(prompt_type, **kwargs):
    """
    Build a complete prompt with system prompt, template, and user data.
    """
    config = get_prompt(prompt_type)

    fireflies_data = kwargs.get('fireflies_data')
    if fireflies_data and fireflies_data.get('content'):
        fireflies_section = (
            "\n**RECRUITER-LED INTERVIEW TRANSCRIPT:**\n"
            f"Title: {fireflies_data.get('metadata', {}).get('title', 'N/A')}\n"
            f"{fireflies_data['content']}"
        )
    else:
        fireflies_section = "**RECRUITER-LED INTERVIEW TRANSCRIPT:**\nNot provided."

    format_args = {
        'candidate_data': kwargs.get('candidate_data', ''),
        'job_data': kwargs.get('job_data', ''),
        'interview_data': kwargs.get('interview_data', ''),
        'fireflies_section': fireflies_section,
        'additional_context': kwargs.get('additional_context', '')
    }

    full_system = f"{config['system_prompt']}\n\n**HTML template (paste into ATS)**\n```html\n{config['template']}\n```"
    user_prompt = config['user_prompt'].format(**format_args)

    return f"{full_system}\n\n{user_prompt}"
