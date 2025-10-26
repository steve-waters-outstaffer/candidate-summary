# config/prompts.py - Firestore-backed prompt configuration (backwards compatible)

import structlog
from flask import current_app

log = structlog.get_logger()

def get_available_prompts(prompt_category="single", prompt_type=None):
    """
    Get available prompts from Firestore.

    Args:
        prompt_category (str): "single" or "multiple"
        prompt_type (str): Optional filter - "email", "summary", etc.

    Returns:
        list: List of prompt objects with id, name, type, sort_order
    """
    log.info("prompts.get_available_prompts.called",
             category=prompt_category,
             type=prompt_type)

    try:
        db = current_app.db
        if not db:
            log.error("prompts.get_available_prompts.no_firestore")
            return []

        # Query Firestore for enabled prompts in the specified category
        from google.cloud.firestore_v1.base_query import FieldFilter
        
        query = db.collection('prompts') \
            .where(filter=FieldFilter('category', '==', prompt_category)) \
            .where(filter=FieldFilter('enabled', '==', True)) \
            .order_by('sort_order')

        # Apply type filter if specified
        if prompt_type:
            query = query.where(filter=FieldFilter('type', '==', prompt_type))

        docs = query.stream()

        prompts = []
        for doc in docs:
            data = doc.to_dict()
            prompts.append({
                'id': doc.id,  # Use Firestore document ID as prompt ID
                'name': data.get('name', doc.id),
                'type': data.get('type', 'summary'),
                'sort_order': data.get('sort_order', 999)
            })

        log.info("prompts.get_available_prompts.success",
                 count=len(prompts),
                 category=prompt_category)

        return prompts

    except Exception as e:
        log.error("prompts.get_available_prompts.error", error=str(e))
        return []


def get_prompt(prompt_type, prompt_category="single"):
    """
    Get a specific prompt configuration from Firestore.

    Args:
        prompt_type (str): Document ID of the prompt (slug)
        prompt_category (str): "single" or "multiple"

    Returns:
        dict: Prompt configuration with system_prompt, template, user_prompt
              Returns None if prompt not found
    """
    log.info("prompts.get_prompt.called",
             prompt_id=prompt_type,
             category=prompt_category)

    try:
        db = current_app.db
        if not db:
            log.error("prompts.get_prompt.no_firestore")
            return None

        # Get the prompt document
        doc = db.collection('prompts').document(prompt_type).get()

        if not doc.exists:
            log.warning("prompts.get_prompt.not_found", prompt_id=prompt_type)
            return None

        data = doc.to_dict()

        # Validate category matches
        if data.get('category') != prompt_category:
            log.warning("prompts.get_prompt.category_mismatch",
                        prompt_id=prompt_type,
                        expected=prompt_category,
                        actual=data.get('category'))
            return None

        # Check if enabled
        if not data.get('enabled', False):
            log.warning("prompts.get_prompt.disabled", prompt_id=prompt_type)
            return None

        prompt_config = {
            'system_prompt': data.get('system_prompt', ''),
            'template': data.get('template', ''),
            'user_prompt': data.get('user_prompt', ''),
            'name': data.get('name', prompt_type),
            'type': data.get('type', 'summary')
        }

        log.info("prompts.get_prompt.success",
                 prompt_id=prompt_type,
                 name=prompt_config['name'])

        return prompt_config

    except Exception as e:
        log.error("prompts.get_prompt.error",
                  prompt_id=prompt_type,
                  error=str(e))
        return None


def build_full_prompt(prompt_type, prompt_category="single", **kwargs):
    """
    Build a complete prompt with system prompt, template, and user data.

    Args:
        prompt_type (str): The prompt ID (document ID in Firestore)
        prompt_category (str): "single" or "multiple"
        **kwargs: Additional data for prompt formatting (candidate_data, job_data, etc.)

    Returns:
        str: Complete formatted prompt ready for AI model
    """
    log.info("prompts.build_full_prompt.called",
             prompt_type=prompt_type,
             category=prompt_category)

    config = get_prompt(prompt_type, prompt_category)

    if not config:
        log.error("prompts.build_full_prompt.prompt_not_found",
                  prompt_type=prompt_type)
        return None

    # Build interview section (Quil takes priority over Fireflies)
    quil_data = kwargs.get('quil_data')
    fireflies_data = kwargs.get('fireflies_data')

    interview_parts = []

    if quil_data and quil_data.get('summary_html'):
        interview_parts.append(
            "\n**RECRUITER-LED INTERVIEW (from Quil):**\n"
            f"Link: {quil_data.get('quil_link', 'N/A')}\n"
            f"{quil_data['summary_html']}"
        )

    if fireflies_data and fireflies_data.get('content') and not quil_data:
        # Only include Fireflies if no Quil data
        interview_parts.append(
            "\n**RECRUITER-LED INTERVIEW (from Fireflies):**\n"
            f"Title: {fireflies_data.get('metadata', {}).get('title', 'N/A')}\n"
            f"{fireflies_data['content']}"
        )

    interview_section = "\n".join(interview_parts) if interview_parts else "**RECRUITER-LED INTERVIEW:**\nNot provided."

    # Prepare format arguments
    format_args = {
        'candidate_data': kwargs.get('candidate_data', ''),
        'job_data': kwargs.get('job_data', ''),
        'interview_data': kwargs.get('interview_data', ''),
        'interview_section': interview_section,
        'fireflies_section': interview_section,  # Alias for backwards compatibility
        'additional_context': kwargs.get('additional_context', ''),
        # Include all other kwargs for multiple-candidate templates
        **kwargs
    }

    # Format the prompt
    full_system = f"{config['system_prompt']}\n\n**HTML template (paste into ATS)**\n```html\n{config['template']}\n```"

    try:
        formatted_user_prompt = config['user_prompt'].format(**format_args)
    except KeyError as e:
        log.error("prompts.build_full_prompt.missing_key",
                  prompt_type=prompt_type,
                  missing_key=str(e))
        return None

    log.info("prompts.build_full_prompt.success", prompt_type=prompt_type)

    # Return combined prompt (same format as original)
    return f"{full_system}\n\n{formatted_user_prompt}"