import os
import re
import requests
import logging
import io
from urllib.parse import urlparse
import google.generativeai as genai
from file_converter import convert_to_supported_format, UnsupportedFileTypeError
from config.prompts import build_full_prompt

# ==============================================================================
# LOGGING & API CONFIGURATION
# ==============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RECRUITCRM_BASE_URL = "https://api.recruitcrm.io/v1"
ALPHARUN_BASE_URL = "https://api.alpharun.com/api/v1"
FIREFLIES_GRAPHQL_URL = "https://api.fireflies.ai/graphql"

RECRUITCRM_API_KEY = os.getenv('RECRUITCRM_API_KEY')
ALPHARUN_API_KEY = os.getenv('ALPHARUN_API_KEY')
FIREFLIES_API_KEY = os.getenv('FIREFLIES_API_KEY')

# ==============================================================================
# API HEADER FUNCTIONS
# ==============================================================================

def get_recruitcrm_headers():
    """Returns the authorization headers for RecruitCRM."""
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {RECRUITCRM_API_KEY}"
    }

def get_alpharun_headers():
    """Returns the authorization headers for AlphaRun."""
    return {
        "Authorization": f"Bearer {ALPHARUN_API_KEY}"
    }

# ==============================================================================
# RECRUITCRM API FUNCTIONS
# ==============================================================================

def fetch_recruitcrm_candidate(slug):
    """Fetches a single candidate record from RecruitCRM."""
    url = f"{RECRUITCRM_BASE_URL}/candidates/{slug}"
    logger.info(f"LOG: Fetching candidate from {url}")
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        logger.info(f"LOG: RecruitCRM candidate API status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"!!! ERROR: RecruitCRM candidate API failed. Body: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"!!! EXCEPTION during candidate fetch: {e}")
        return None

def fetch_recruitcrm_job(slug):
    """Fetches a single job record from RecruitCRM."""
    url = f"{RECRUITCRM_BASE_URL}/jobs/{slug}"
    logger.info(f"LOG: Fetching job from {url}")
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        logger.info(f"LOG: RecruitCRM job API status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"!!! ERROR: RecruitCRM job API failed. Body: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"!!! EXCEPTION during job fetch: {e}")
        return None

# ==============================================================================
# ALPHARUN API FUNCTIONS
# ==============================================================================

def fetch_alpharun_interview(job_opening_id, interview_id):
    """Fetches interview data from AlphaRun using the job opening ID."""
    url = f"{ALPHARUN_BASE_URL}/job-openings/{job_opening_id}/interviews/{interview_id}"
    logger.info(f"LOG: Fetching interview from {url}")
    try:
        response = requests.get(url, headers=get_alpharun_headers())
        logger.info(f"LOG: AlphaRun interview API status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"!!! ERROR: AlphaRun interview API failed. Body: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"!!! EXCEPTION during interview fetch: {e}")
        return None

# ==============================================================================
# FIREFLIES.AI API FUNCTIONS
# ==============================================================================

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

def extract_fireflies_transcript_id(s: str) -> str | None:
    """Parses a string to find a Fireflies transcript ID."""
    s = s.strip()
    if s.startswith("http://") or s.startswith("https://"):
        try:
            path_segment = urlparse(s).path.rsplit("/", 1)[-1]
            parts = path_segment.split("::")
            if len(parts) == 2 and ULID_PATTERN.fullmatch(parts[1]):
                return parts[1]
        except (IndexError, ValueError):
            return None
    if ULID_PATTERN.fullmatch(s):
        return s
    return None

def fetch_fireflies_transcript(transcript_id: str) -> dict:
    """Fetches a transcript from the Fireflies GraphQL API using the server's API key."""
    headers = {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }
    query = """
    query Transcript($id: String!) {
      transcript(id: $id) {
        id title date duration transcript_url
        speakers { id name }
        sentences { index speaker_name start_time end_time text }
      }
    }
    """
    variables = {"id": transcript_id}
    logger.info(f"LOG: Fetching Fireflies transcript ID: {transcript_id}")
    try:
        resp = requests.post(
            FIREFLIES_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            logger.error(f"!!! ERROR: Fireflies GraphQL error: {payload['errors']}")
            return None
        return payload.get("data", {}).get("transcript")
    except requests.exceptions.RequestException as e:
        logger.error(f"!!! EXCEPTION during Fireflies fetch: {e}")
        return None

def normalise_fireflies_transcript(tr: dict) -> dict:
    """Produces a compact, LLM-ready JSON from the raw transcript data."""
    logger.info("LOG: Normalising Fireflies transcript for LLM.")
    speakers = [s.get("name") for s in (tr.get("speakers") or []) if s and s.get("name")]
    lines = []
    for s in (tr.get("sentences") or []):
        speaker = s.get("speaker_name") or "Unknown"
        text = s.get("text") or ""
        lines.append(f"{speaker}: {text}".strip())

    return {
        "metadata": {
            "title": tr.get("title"),
            "url": tr.get("transcript_url"),
            "speakers": speakers,
        },
        "content": "\n".join(lines),
    }

# ==============================================================================
# GOOGLE GEMINI API FUNCTIONS
# ==============================================================================

def upload_resume_to_gemini(resume_data: dict) -> dict | None:
    """
    Downloads a resume, converts it to a supported format if necessary,
    and uploads it to the Gemini File API.
    Returns the file object from the Gemini API if successful.
    """
    if not resume_data or 'file_link' not in resume_data or 'filename' not in resume_data:
        logger.info("LOG: No valid resume data provided.")
        return None

    file_link = resume_data['file_link']
    filename = resume_data['filename']
    logger.info(f"LOG: Attempting to process resume: {filename}")

    try:
        # 1. Download the resume file from RecruitCRM
        response = requests.get(file_link, timeout=30)
        response.raise_for_status()
        resume_bytes = response.content
        logger.info(f"LOG: Successfully downloaded {filename} from RecruitCRM.")

        # 2. Convert the file to a supported format (e.g., text/plain) if needed
        try:
            converted_bytes, supported_mime_type = convert_to_supported_format(
                file_bytes=resume_bytes,
                original_filename=filename
            )
            logger.info(f"LOG: File '{filename}' processed for upload with MIME type '{supported_mime_type}'.")
        except UnsupportedFileTypeError as e:
            # Log a warning but don't crash the whole process.
            # The summary generation will proceed without the resume.
            logger.warning(f"!!! WARNING: Could not process resume. {e}")
            return None

        # 3. Upload the processed file content to the Gemini File API
        gemini_file = genai.upload_file(
            path=io.BytesIO(converted_bytes),
            display_name=filename,
            mime_type=supported_mime_type # <-- Use the new supported mime type
        )
        logger.info(f"LOG: Successfully uploaded resume to Gemini. URI: {gemini_file.uri}")

        return gemini_file

    except requests.exceptions.RequestException as e:
        logger.error(f"!!! EXCEPTION during resume download: {e}")
        return None
    except Exception as e:
        # This will catch errors from the Gemini API upload itself
        logger.error(f"!!! EXCEPTION during resume upload to Gemini: {e}")
        return None

def generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data=None, gemini_resume_file=None, model=None):
    """Generate HTML summary using Google Gemini and clean the response."""
    logger.info(f"LOG: Generating HTML summary with Gemini using prompt type: {prompt_type}")

    prompt_text = build_full_prompt(
        prompt_type=prompt_type,
        candidate_data=candidate_data,
        job_data=job_data,
        interview_data=interview_data,
        additional_context=additional_context,
        fireflies_data=fireflies_data
    )

    prompt_contents = [prompt_text]

    if gemini_resume_file:
        prompt_contents.append(gemini_resume_file)
        logger.info("LOG: Appending resume file to Gemini prompt.")

    try:
        response = model.generate_content(prompt_contents)
        raw_html = response.text
        logger.info("LOG: Cleaning Gemini response.")
        cleaned_html = raw_html.strip()
        if cleaned_html.startswith("```html"):
            cleaned_html = cleaned_html[7:]
        if cleaned_html.endswith("```"):
            cleaned_html = cleaned_html[:-3]
        return cleaned_html.strip()
    except Exception as e:
        logger.error(f"!!! EXCEPTION during Gemini summary generation: {e}")
        return None

def generate_ai_response(prompt_text: str, files: list = None, model=None) -> str | None:
    """Generates a response from the AI model, optionally with files."""
    logger.info("Generating AI response...")
    try:
        contents = [prompt_text]
        if files:
            contents.extend(files)
        response = model.generate_content(contents)
        return response.text
    except Exception as e:
        logger.error(f"EXCEPTION during AI response generation: {e}")
        return None
