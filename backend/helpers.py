import os
import logging
import requests
import mimetypes
import tempfile
from urllib.parse import urlparse
import google.generativeai as genai
from config.prompts import build_full_prompt
from file_converter import convert_to_supported_format, UnsupportedFileTypeError

# --- Environment Variable Checks ---
RECRUITCRM_API_KEY = os.getenv('RECRUITCRM_API_KEY')
ALPHARUN_API_KEY = os.getenv('ALPHARUN_API_KEY')
FIREFLIES_API_KEY = os.getenv('FIREFLIES_API_KEY')

# ==============================================================================
# 1. AUTHENTICATION HELPERS
# ==============================================================================

def get_recruitcrm_headers():
    """Returns the authorization headers for the RecruitCRM API."""
    if not RECRUITCRM_API_KEY:
        raise ValueError("RECRUITCRM_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {RECRUITCRM_API_KEY}',
        'Content-Type': 'application/json'
    }

def get_alpharun_headers():
    """Returns the authorization headers for the AlphaRun API."""
    if not ALPHARUN_API_KEY:
        raise ValueError("ALPHARUN_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {ALPHARUN_API_KEY}',
        'Content-Type': 'application/json'
    }

def get_fireflies_headers():
    """Returns the authorization headers for the Fireflies.ai API."""
    if not FIREFLIES_API_KEY:
        raise ValueError("FIREFLIES_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {FIREFLIES_API_KEY}',
        'Content-Type': 'application/json'
    }

# ==============================================================================
# 2. DATA FETCHING HELPERS
# ==============================================================================

def fetch_recruitcrm_candidate(slug):
    """Fetches candidate data from RecruitCRM using the candidate's slug."""
    url = f'https://api.recruitcrm.io/v1/candidates/{slug}'
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching RecruitCRM candidate {slug}: {e}")
        return None


def fetch_candidate_interview_id(slug):
    """Fetches a candidate's AI Interview ID from RecruitCRM."""
    candidate_data = fetch_recruitcrm_candidate(slug)
    if not candidate_data:
        return None

    candidate_details = candidate_data.get('data', candidate_data)
    for field in candidate_details.get('custom_fields', []):
        if isinstance(field, dict) and field.get('field_name') == 'AI Interview ID':
            value = field.get('value')
            if value:
                return value.split('?')[0]
            break
    return None

def fetch_recruitcrm_job(slug, include_custom_fields=True):
    """Fetches job data from RecruitCRM using the job's slug.

    Args:
        slug (str): The job slug/ID in RecruitCRM.
        include_custom_fields (bool): Whether to request custom fields as part of
            the response. Defaults to ``True``.

    Returns:
        dict | None: The JSON response from RecruitCRM, or ``None`` if the
        request fails.
    """
    url = f'https://api.recruitcrm.io/v1/jobs/{slug}'
    params = {'include': 'custom_fields'} if include_custom_fields else None
    try:
        response = requests.get(
            url,
            headers=get_recruitcrm_headers(),
            params=params
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching RecruitCRM job {slug}: {e}")
        return None

def fetch_hiring_pipeline():
    """Fetches the entire hiring pipeline (all possible stages)."""
    url = "https://api.recruitcrm.io/v1/hiring-pipeline"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching hiring pipeline: {e}")
        return []

def fetch_recruitcrm_assigned_candidates(job_slug, status_id=None):
    """Fetches assigned candidates for a job from RecruitCRM."""
    url = f"https://api.recruitcrm.io/v1/jobs/{job_slug}/assigned-candidates"
    params = {'status_id': status_id} if status_id else {}
    try:
        response = requests.get(url, headers=get_recruitcrm_headers(), params=params)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching assigned candidates for job {job_slug}: {e}")
        return []

def fetch_alpharun_interview(job_opening_id, interview_id):
    """Fetches interview data from AlphaRun."""
    url = f"https://alpharun.com/api/v1/job_openings/{job_opening_id}/interviews/{interview_id}"
    try:
        response = requests.get(url, headers=get_alpharun_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching AlphaRun interview {interview_id}: {e}")
        return None

def extract_fireflies_transcript_id(url):
    """Extracts the transcript ID from a Fireflies.ai meeting URL."""
    try:
        path_segments = urlparse(url).path.split('/')
        if 'transcript' in path_segments:
            return path_segments[path_segments.index('transcript') + 1]
    except (ValueError, IndexError) as e:
        logging.error(f"Could not extract transcript ID from URL {url}: {e}")
    return None

def fetch_fireflies_transcript(transcript_id):
    """Fetches a transcript from Fireflies.ai using its ID."""
    url = f"https://api.fireflies.ai/v1/transcript/{transcript_id}"
    try:
        response = requests.get(url, headers=get_fireflies_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Fireflies transcript {transcript_id}: {e}")
        return None

# ==============================================================================
# 3. DATA PROCESSING & GENERATION HELPERS
# ==============================================================================

def normalise_fireflies_transcript(raw_transcript):
    """Normalises raw Fireflies transcript data into a structured format for the AI model."""
    if not raw_transcript:
        return {'metadata': {}, 'content': "Not provided."}

    title = raw_transcript.get('title', 'N/A')
    sentences = raw_transcript.get('sentences', [])
    content = '\n'.join([f"{s.get('speaker_name', 'Unknown')}: {s.get('text', '')}" for s in sentences])

    return {
        'metadata': {'title': title},
        'content': content or "Transcript content is empty."
    }

def upload_resume_to_gemini(resume_info):
    """Downloads a resume, determines its MIME type, and uploads it to the Gemini API."""
    if not resume_info:
        logging.warning("No resume info object provided.")
        return None

    resume_url = resume_info.get('file_link') or resume_info.get('url')

    if not resume_url:
        logging.warning(f"No 'file_link' or 'url' found in resume_info object: {resume_info}")
        return None

    try:
        file_response = requests.get(resume_url)
        file_response.raise_for_status()

        original_filename = resume_info.get('filename', 'resume.bin')
        
        # Convert file to supported format if needed
        try:
            converted_bytes, final_mime_type = convert_to_supported_format(
                file_response.content, 
                original_filename
            )
            logging.info(f"File '{original_filename}' converted to MIME type '{final_mime_type}'")
        except UnsupportedFileTypeError as e:
            logging.error(f"Cannot upload file '{original_filename}': {e}")
            return None

        logging.info(f"Uploading '{original_filename}' with MIME type '{final_mime_type}' to Gemini.")

        # Create temporary file with proper extension for final format
        file_ext = '.txt' if final_mime_type == 'text/plain' else os.path.splitext(original_filename)[1]
        
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        try:
            tmp_file.write(converted_bytes)
            tmp_file.close()  # Close file before Gemini tries to access it
            
            gemini_file = genai.upload_file(
                path=tmp_file.name,
                display_name=original_filename,
                mime_type=final_mime_type
            )
            
            logging.info(f"Completed uploading '{gemini_file.display_name}' to Gemini.")
            return gemini_file
            
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file.name)
            except OSError as cleanup_error:
                logging.warning(f"Could not clean up temp file {tmp_file.name}: {cleanup_error}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading resume from {resume_url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during resume upload: {e}")
        return None

def generate_ai_response(model, prompt_parts):
    """Generates a response from the AI model."""
    try:
        response = model.generate_content(prompt_parts)
        return response.text
    except Exception as e:
        logging.error(f"Error during AI content generation: {e}")
        return None

def generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data, gemini_resume_file, model):
    """Builds the full prompt and generates an HTML summary using the AI model."""
    candidate_details = candidate_data.get('data', candidate_data)
    job_details = job_data.get('data', job_data)
    interview_details = interview_data.get('data', interview_data) if interview_data else {}

    full_prompt = build_full_prompt(
        prompt_type,
        "single",
        candidate_data=candidate_details,
        job_data=job_details,
        interview_data=interview_details,
        additional_context=additional_context,
        fireflies_data=fireflies_data
    )

    prompt_parts = [full_prompt]
    if gemini_resume_file:
        prompt_parts.append(gemini_resume_file)
        logging.info("Resume file included in the prompt for AI generation.")

    return generate_ai_response(model, prompt_parts)