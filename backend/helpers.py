import os
import re
import requests
import logging
import io
from urllib.parse import urlparse
import google.generativeai as genai
from file_converter import convert_to_supported_format, UnsupportedFileTypeError

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
# UTILITY FUNCTIONS
# ==============================================================================

def get_slug_from_url(url: str) -> str | None:
    """Extracts the slug from a RecruitCRM or similar URL."""
    if not url:
        return None
    match = re.search(r'/([\w-]+)$', url)
    if match:
        return match.group(1)
    return url  # Fallback

# ==============================================================================
# API HEADER FUNCTIONS
# ==============================================================================

def get_recruitcrm_headers():
    """Returns the authorization headers for RecruitCRM."""
    return {"Authorization": f"Bearer {RECRUITCRM_API_KEY}"}

def get_alpharun_headers():
    """Returns the authorization headers for AlphaRun."""
    return {"Authorization": f"Bearer {ALPHARUN_API_KEY}"}

# ==============================================================================
# RECRUITCRM API FUNCTIONS
# ==============================================================================

def fetch_recruitcrm_candidate(slug: str) -> dict | None:
    """Fetches a single candidate record from RecruitCRM."""
    url = f"{RECRUITCRM_BASE_URL}/candidates/{slug}"
    logger.info(f"Fetching RecruitCRM candidate from {url}")
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"EXCEPTION during RecruitCRM candidate fetch for slug {slug}: {e}")
        return None

def fetch_recruitcrm_job(slug: str) -> dict | None:
    """Fetches a single job record from RecruitCRM."""
    url = f"{RECRUITCRM_BASE_URL}/jobs/{slug}"
    logger.info(f"Fetching RecruitCRM job from {url}")
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"EXCEPTION during RecruitCRM job fetch for slug {slug}: {e}")
        return None

# ==============================================================================
# ALPHARUN API FUNCTIONS
# ==============================================================================

def fetch_alpharun_interview(job_opening_id: str, interview_id: str) -> dict | None:
    """Fetches interview data from AlphaRun."""
    if not job_opening_id or not interview_id:
        logger.warning("Skipping AlphaRun fetch due to missing job_opening_id or interview_id.")
        return None

    url = f"{ALPHARUN_BASE_URL}/job-openings/{job_opening_id}/interviews/{interview_id}"
    logger.info(f"Fetching AlphaRun interview from {url}")
    try:
        response = requests.get(url, headers=get_alpharun_headers())
        if response.status_code == 200:
            return response.json()
        logger.error(f"AlphaRun interview API failed with status {response.status_code}. Body: {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"EXCEPTION during AlphaRun interview fetch: {e}")
        return None

# ==============================================================================
# FIREFLIES.AI API FUNCTIONS
# ==============================================================================

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

def extract_fireflies_transcript_id(s: str) -> str | None:
    """Parses a string to find a Fireflies transcript ID."""
    s = s.strip()
    if s.startswith("http"):
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

def fetch_fireflies_transcript(transcript_id: str) -> dict | None:
    """Fetches a transcript from the Fireflies GraphQL API."""
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
    logger.info(f"Fetching Fireflies transcript ID: {transcript_id}")
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
            logger.error(f"Fireflies GraphQL error: {payload['errors']}")
            return None
        return payload.get("data", {}).get("transcript")
    except requests.exceptions.RequestException as e:
        logger.error(f"EXCEPTION during Fireflies fetch: {e}")
        return None

def normalise_fireflies_transcript(tr: dict) -> dict:
    """Produces a compact, LLM-ready JSON from the raw transcript data."""
    if not tr: return {}
    speakers = [s.get("name") for s in (tr.get("speakers") or []) if s and s.get("name")]
    lines = [f"{(s.get('speaker_name') or 'Unknown')}: {(s.get('text') or '')}".strip() for s in (tr.get("sentences") or [])]
    return {
        "metadata": {"title": tr.get("title"), "url": tr.get("transcript_url"), "speakers": speakers},
        "content": "\n".join(lines),
    }

# ==============================================================================
# GOOGLE GEMINI API FUNCTIONS
# ==============================================================================

def upload_resume_to_gemini(resume_data: dict) -> dict | None:
    """Downloads, converts, and uploads a resume to the Gemini File API."""
    if not resume_data or 'file_link' not in resume_data or 'filename' not in resume_data:
        return None

    file_link = resume_data['file_link']
    filename = resume_data['filename']
    logger.info(f"Processing resume: {filename}")
    try:
        response = requests.get(file_link, timeout=30)
        response.raise_for_status()
        resume_bytes = response.content

        converted_bytes, supported_mime_type = convert_to_supported_format(
            file_bytes=resume_bytes, original_filename=filename
        )

        gemini_file = genai.upload_file(
            path=io.BytesIO(converted_bytes),
            display_name=filename,
            mime_type=supported_mime_type
        )
        logger.info(f"Successfully uploaded resume to Gemini. URI: {gemini_file.uri}")
        return gemini_file

    except requests.exceptions.RequestException as e:
        logger.error(f"EXCEPTION during resume download for {filename}: {e}")
    except UnsupportedFileTypeError as e:
        logger.warning(f"Could not process resume {filename}. {e}")
    except Exception as e:
        logger.error(f"EXCEPTION during resume upload to Gemini for {filename}: {e}")
    return None

def generate_ai_response(prompt_text: str, files: list = None) -> str | None:
    """Generates a response from the AI model, optionally with files."""
    logger.info("Generating AI response...")
    try:
        contents = [prompt_text]
        if files:
            contents.extend(files)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(contents)
        return response.text
    except Exception as e:
        logger.error(f"EXCEPTION during AI response generation: {e}")
        return None

def generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data=None, gemini_resume_file=None):
    """Generate HTML summary using Google Gemini and clean the response."""
    from config.prompts import build_full_prompt

    logger.info(f"Generating HTML summary with prompt: {prompt_type}")

    prompt_text = build_full_prompt(
        prompt_type=prompt_type,
        candidate_data=candidate_data,
        job_data=job_data,
        interview_data=interview_data,
        additional_context=additional_context,
        fireflies_data=fireflies_data
    )

    files_to_upload = [gemini_resume_file] if gemini_resume_file else []

    raw_html = generate_ai_response(prompt_text, files=files_to_upload)

    if raw_html:
        logger.info("Cleaning Gemini response.")
        cleaned_html = raw_html.strip()
        if cleaned_html.startswith("```html"):
            cleaned_html = cleaned_html[7:]
        if cleaned_html.endswith("```"):
            cleaned_html = cleaned_html[:-3]
        return cleaned_html.strip()
    return None