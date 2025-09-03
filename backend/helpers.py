import os
import logging
import requests
import re
from flask import current_app
from urllib.parse import urlparse
from re import sub, MULTILINE
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

# --- Constants  ---
GRAPHQL_URL = "https://api.fireflies.ai/graphql"
TRANSCRIPT_QUERY = """
query Transcript($id: String!) {
  transcript(id: $id) {
    id
    title
    date
    duration
    transcript_url
    speakers { id name }
    sentences {
      index
      speaker_name
      start_time
      end_time
      text
      raw_text
    }
  }
}
"""

# ==============================================================================
# 1. AUTHENTICATION HELPERS
# ==============================================================================

def get_recruitcrm_headers():
    """Returns the authorization headers for the RecruitCRM API."""
    if not RECRUITCRM_API_KEY:
        raise ValueError("RECRUITCRM_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {RECRUITCRM_API_KEY}',
        'Accept': 'application/json'  # Use 'Accept' instead of 'Content-Type'
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


# In backend/helpers.py

def fetch_candidate_interview_id(candidate_slug, job_slug=None):
    """
    Fetches the AI Interview ID for a candidate.
    It first checks the job-specific associated fields, which is the new primary location.
    If not found, it falls back to checking the general custom fields on the candidate's record.
    """
    # 1. New Method: Check job-associated fields first
    if job_slug:
        current_app.logger.info(f"--- Starting AI Interview ID search for cand: {candidate_slug}, job: {job_slug} ---")
        job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug)

        if job_specific_fields:
            current_app.logger.info(f"  [1] Checking NEW location (Job-Associated Fields)...")
            current_app.logger.info(f"  [1a] Fields returned from API: {job_specific_fields}")
            for field_key, field_data in job_specific_fields.items():
                # Check if the field is a dictionary and has a 'label'
                if isinstance(field_data, dict) and 'label' in field_data:
                    current_app.logger.info(f"    - Checking field -> Label: '{field_data.get('label')}', Value: '{field_data.get('value')}'")
                    if field_data.get('label') == 'AI Interview ID':
                        interview_id = field_data.get('value')
                        if interview_id:
                            current_app.logger.info(f"  [SUCCESS] Found AI Interview ID '{interview_id}' in new location.")
                            return interview_id
            current_app.logger.info("  [1b] Did not find a matching 'AI Interview ID' label with a value.")
        else:
            current_app.logger.info("  [1] No job-associated fields were returned from the API for this candidate/job.")

    # 2. Fallback Method: Check the main custom fields on the candidate record
    current_app.logger.info("  [2] Checking FALLBACK location (Candidate Custom Fields)...")
    candidate_data = fetch_recruitcrm_candidate(candidate_slug)
    if candidate_data:
        candidate_details = candidate_data.get('data', candidate_data)
        custom_fields = candidate_details.get('custom_fields', [])
        current_app.logger.info(f"  [2a] Fields returned from API: {custom_fields}")
        for field in custom_fields:
            if isinstance(field, dict) and 'field_name' in field:
                current_app.logger.info(f"    - Checking field -> Name: '{field.get('field_name')}', Value: '{field.get('value')}'")
                if field.get('field_name') == 'AI Interview ID':
                    interview_id = field.get('value')
                    if interview_id:
                        current_app.logger.info(f"  [SUCCESS] Found AI Interview ID '{interview_id}' in fallback location.")
                        return interview_id
        current_app.logger.info("  [2b] Did not find a matching 'AI Interview ID' field name with a value.")
    else:
        current_app.logger.warning("  [2] Could not fetch candidate data for fallback check.")


    # 3. If not found in either location
    current_app.logger.info(f"--- No AI Interview ID found for candidate {candidate_slug}. Returning None. ---")
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

def get_recruitcrm_headers():
    """Returns the authorization headers for RecruitCRM API calls."""
    return {
        'Authorization': f'Bearer {os.getenv("RECRUITCRM_API_KEY")}',
        'Accept': 'application/json'
    }

def push_to_recruitcrm_internal(candidate_slug, html_summary):
    """Internal function to push summary, returns success status."""
    logging.info(f"\n--- Calling push_to_recruitcrm_internal for {candidate_slug} ---")
    try:
        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {'candidate_summary': (None, html_summary)}
        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        if response.status_code == 200:
            logging.info(f"Successfully pushed summary for {candidate_slug}")
            return True
        else:
            logging.error(f"Failed to push summary for {candidate_slug}: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Exception in push_to_recruitcrm_internal for {candidate_slug}: {e}")
        return False

def fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug):
    """Fetches job-specific custom fields for a candidate from RecruitCRM."""
    if not RECRUITCRM_API_KEY:
        logging.error("RecruitCRM API key is not set.")
        return None
    url = f"https://api.recruitcrm.io/v1/candidates/associated-field/{candidate_slug}/{job_slug}"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        if response.status_code == 200:
            logging.info(f"Successfully fetched job-specific fields for candidate {candidate_slug} and job {job_slug}")
            return response.json().get('data', {})
        else:
            logging.error(f"Failed to fetch job-specific fields for candidate {candidate_slug} and job {job_slug}: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while fetching job-specific fields: {e}")
        return None

def fetch_recruitcrm_assigned_candidates(job_slug, status_id=None):
    """Fetches assigned candidates for a job from RecruitCRM."""
    url = f"https://api.recruitcrm.io/v1/jobs/{job_slug}/assigned-candidates"
    params = {'status_id': status_id} if status_id else {}
    try:
        response = requests.get(url, headers=get_recruitcrm_headers(), params=params)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching assigned candidatez for job {job_slug}: {e}")
        return []

def fetch_alpharun_interview(job_opening_id, interview_id):
    """Fetches interview data from AlphaRun."""
    url = f"https://api.alpharun.com/api/v1/job-openings/{job_opening_id}/interviews/{interview_id}"

    try:
        response = requests.get(url, headers=get_alpharun_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching AlphaRun interview {interview_id}: {e}")
        return None

# This pattern is crucial for validating the ID.
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

def extract_fireflies_transcript_id(s: str) -> str | None:
    """
    Parses a string to find a Fireflies transcript ID.

    Args:
        s: The input string, which can be a full URL or a standalone ID.

    Returns:
        The extracted 26-character ID, or None if not found.
    """
    if not s:
        return None

    s = s.strip()
    # If user pasted a full URL, parse ".../view/<slug>::<ID>"
    if s.startswith("http://") or s.startswith("https://"):
        try:
            path_segment = urlparse(s).path.rsplit("/", 1)[-1]
            parts = path_segment.split("::")
            if len(parts) == 2 and ULID_PATTERN.fullmatch(parts[1]):
                return parts[1]
        except (IndexError, ValueError):
            return None
        return None
    # If they pasted just the ID
    if ULID_PATTERN.fullmatch(s):
        return s
    return None


def fetch_fireflies_transcript(transcript_id: str) -> dict | None:
    """
    Fetches a transcript from Fireflies.ai using GraphQL.
    """
    api_key = os.getenv('FIREFLIES_API_KEY')
    if not api_key:
        logging.error("FIREFLIES_API_KEY environment variable not set.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": TRANSCRIPT_QUERY,
        "variables": {"id": transcript_id}
    }

    try:
        resp = requests.post(
            GRAPHQL_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        response_data = resp.json()

        if "errors" in response_data:
            logging.error(f"GraphQL error fetching Fireflies transcript {transcript_id}: {response_data['errors']}")
            return None

        return response_data.get("data", {}).get("transcript")

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error fetching Fireflies transcript {transcript_id}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"JSON decode error fetching Fireflies transcript {transcript_id}.")
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

    html_summary = generate_ai_response(model, prompt_parts)

    if html_summary:
        # --- FIX: Strip markdown code fences from the AI's response ---
        # The model sometimes wraps its HTML output in ```html ... ```, which needs to be removed.
        cleaned_summary = sub(r'^```(html)?\n|```$', '', html_summary, flags=MULTILINE).strip()
        return cleaned_summary

    return html_summary