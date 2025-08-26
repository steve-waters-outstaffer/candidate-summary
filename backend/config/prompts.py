import os
import json
import logging

SINGLE_CANDIDATE_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'single-candidate-prompts')
MULTIPLE_CANDIDATES_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'multiple-candidates-prompts')

def get_available_prompts(prompt_category="single"):
    """Scans the specified prompts directory and returns a list of available prompt configurations.
    
    Args:
        prompt_category (str): "single" for single-candidate-prompts or "multiple" for multiple-candidates-prompts
    """
    prompts = []
    
    # Select the appropriate directory
    if prompt_category == "single":
        prompts_dir = SINGLE_CANDIDATE_PROMPTS_DIR
    elif prompt_category == "multiple":
        prompts_dir = MULTIPLE_CANDIDATES_PROMPTS_DIR
    else:
        raise ValueError(f"Invalid prompt_category: {prompt_category}. Use 'single' or 'multiple'.")
    
    if not os.path.exists(prompts_dir):
        logging.error(f"Prompts directory not found at: {prompts_dir}")
        return prompts

    for root, dirs, files in os.walk(prompts_dir):
        for file in files:
            if file.endswith('.json'):
                try:
                    relative_path = os.path.relpath(os.path.join(root, file), prompts_dir)
                    prompt_id = os.path.splitext(relative_path.replace(os.path.sep, '.'))[0]
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        prompts.append({
                            'id': prompt_id,
                            'name': data.get('name', prompt_id),
                            # --- CHANGE 1: Read the sort_order key ---
                            'sort_order': data.get('sort_order', 999) # Defaults to 999 if key is missing
                        })
                except Exception as e:
                    logging.error(f"Error loading prompt {file}: {e}")

    # --- CHANGE 2: Sort by the new 'sort_order' key ---
    return sorted(prompts, key=lambda p: p['sort_order'])

def get_prompt(prompt_type="recruitment.detailed", prompt_category="single"):
    """Retrieve a specific prompt configuration from its JSON file.
    
    Args:
        prompt_type (str): The prompt type (e.g., "recruitment.detailed", "candidate-submission")
        prompt_category (str): "single" for single-candidate-prompts or "multiple" for multiple-candidates-prompts
    """
    # Select the appropriate directory
    if prompt_category == "single":
        prompts_dir = SINGLE_CANDIDATE_PROMPTS_DIR
    elif prompt_category == "multiple":
        prompts_dir = MULTIPLE_CANDIDATES_PROMPTS_DIR
    else:
        raise ValueError(f"Invalid prompt_category: {prompt_category}. Use 'single' or 'multiple'.")
    
    file_path = os.path.join(prompts_dir, *prompt_type.split('.')) + '.json'
    if not os.path.exists(file_path):
        raise ValueError(f"Prompt type '{prompt_type}' not found at {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading or parsing prompt file {file_path}: {e}")
        raise

def build_full_prompt(prompt_type, prompt_category="single", **kwargs):
    """
    Build a complete prompt with system prompt, template, and user data.
    
    Args:
        prompt_type (str): The prompt type (e.g., "recruitment.detailed", "candidate-submission")
        prompt_category (str): "single" for single-candidate-prompts or "multiple" for multiple-candidates-prompts
        **kwargs: Additional data for prompt formatting
    """
    config = get_prompt(prompt_type, prompt_category)

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
        'additional_context': kwargs.get('additional_context', ''),
        # Add all other kwargs for multiple-candidate templates
        **kwargs
    }

    full_system = f"{config['system_prompt']}\n\n**HTML template (paste into ATS)**\n```html\n{config['template']}\n```"
    user_prompt = config['user_prompt'].format(**format_args)

    return f"{full_system}\n\n{user_prompt}"
