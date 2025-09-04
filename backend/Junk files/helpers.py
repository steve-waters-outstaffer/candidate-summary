import os
import structlog
import requests
import re
from re import sub, MULTILINE
import tempfile
from urllib.parse import urlparse
import google.generativeai as genai
from flask import json
import io

# Initialize logger at the top
log = structlog.get_logger()

# --- Safely import new dependencies ---
try:
    import magic
except ImportError:
    log.error("The 'python-magic' library is not installed or its dependency 'libmagic' is missing. Please install it.")
    magic = None

try:
    import docx
except ImportError:
    log.error("The 'python-docx' library is not installed. Please install it.")
    docx = None


from config.prompts import build_full_prompt


# --- Environment Variable Checks ---
RECRUITCRM_API_KEY = os.getenv("RECRUITCRM_API_KEY")
ALPHARUN_API_KEY = os.getenv("ALPHARUN_API_KEY")
FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY")

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
        "Authorization": f"Bearer {RECRUITCRM_API_KEY}",
        "Accept": "application/json",
    }


def get_alpharun_headers():
    """Returns the authorization headers for the AlphaRun API."""
    if not ALPHARUN_API_KEY:
        raise ValueError("ALPHARUN_API_KEY is not set in the environment.")
    return {
        "Authorization": f"Bearer {ALPHARUN_API_KEY}",
        "Content-Type": "application/json",
    }


def get_fireflies_headers():
    """Returns the authorization headers for the Fireflies.ai API."""
    if not FIREFLIES_API_KEY:
        raise ValueError("FIREFLIES_API_KEY is not set in the environment.")
    return {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }


# ==============================================================================
# 2. DATA FETCHING HELPERS
# ==============================================================================


def fetch_recruitcrm_candidate(slug):
    """Fetches candidate data from RecruitCRM using the candidate's slug."""
    url = f"https://api.recruitcrm.io/v1/candidates/{slug}"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error(
            "helpers.fetch_recruitcrm_candidate.failed",
            slug=slug,
            error=str(e),
        )
        return None


def fetch_candidate_interview_id(candidate_slug, job_slug=None):
    """
    Fetches the AI Interview ID for a candidate.
    It first checks the job-specific associated fields, which is the new primary location.
    If not found, it falls back to checking the general custom fields on the candidate's record.
    """
    if job_slug:
        log.info(
            "helpers.fetch_candidate_interview_id.start",
            candidate_slug=candidate_slug,
            job_slug=job_slug,
        )
        job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(
            candidate_slug, job_slug
        )

        if job_specific_fields:
            log.info("helpers.fetch_candidate_interview_id.check_job_fields")
            for field_key, field_data in job_specific_fields.items():
                if isinstance(field_data, dict) and "label" in field_data:
                    if field_data.get("label") == "AI Interview ID":
                        interview_id = field_data.get("value")
                        if interview_id:
                            log.info(
                                "helpers.fetch_candidate_interview_id.found_in_job_fields",
                                interview_id=interview_id,
                            )
                            return interview_id
            log.info("helpers.fetch_candidate_interview_id.no_match_in_job_fields")
        else:
            log.info("helpers.fetch_candidate_interview_id.no_job_fields")

    log.info("helpers.fetch_candidate_interview_id.check_candidate_fields")
    candidate_data = fetch_recruitcrm_candidate(candidate_slug)
    if candidate_data:
        candidate_details = candidate_data.get("data", candidate_data)
        custom_fields = candidate_details.get("custom_fields", [])
        for field in custom_fields:
            if isinstance(field, dict) and "field_name" in field:
                if field.get("field_name") == "AI Interview ID":
                    interview_id = field.get("value")
                    if interview_id:
                        log.info(
                            "helpers.fetch_candidate_interview_id.found_in_candidate_fields",
                            interview_id=interview_id,
                        )
                        return interview_id
        log.info(
            "helpers.fetch_candidate_interview_id.no_match_in_candidate_fields"
        )
    else:
        log.warning(
            "helpers.fetch_candidate_interview_id.candidate_data_unavailable"
        )

    log.info(
        "helpers.fetch_candidate_interview_id.not_found", candidate_slug=candidate_slug
    )
    return None


def fetch_recruitcrm_job(slug, include_custom_fields=True):
    """Fetches job data from RecruitCRM using the job's slug."""
    url = f"https://api.recruitcrm.io/v1/jobs/{slug}"
    params = {"include": "custom_fields"} if include_custom_fields else None
    try:
        response = requests.get(
            url, headers=get_recruitcrm_headers(), params=params
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error(
            "helpers.fetch_recruitcrm_job.failed",
            slug=slug,
            error=str(e),
        )
        return None


def fetch_hiring_pipeline():
    """Fetches the entire hiring pipeline (all possible stages)."""
    url = "https://api.recruitcrm.io/v1/hiring-pipeline"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("helpers.fetch_hiring_pipeline.failed", error=str(e))
        return []


def push_to_recruitcrm_internal(candidate_slug, html_summary):
    """Internal function to push summary, returns success status."""
    log.info(
        "helpers.push_to_recruitcrm_internal.start", candidate_slug=candidate_slug
    )
    try:
        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {"candidate_summary": (None, html_summary)}
        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        if response.status_code == 200:
            log.info(
                "helpers.push_to_recruitcrm_internal.success",
                candidate_slug=candidate_slug,
            )
            return True
        else:
            log.error(
                "helpers.push_to_recruitcrm_internal.failed",
                candidate_slug=candidate_slug,
                status=response.status_code,
            )
            return False
    except Exception as e:
        log.error(
            "helpers.push_to_recruitcrm_internal.exception",
            candidate_slug=candidate_slug,
            error=str(e),
        )
        return False


def fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug):
    """Fetches job-specific custom fields for a candidate from RecruitCRM."""
    if not RECRUITCRM_API_KEY:
        log.error("helpers.fetch_job_specific_fields.missing_api_key")
        return None
    url = f"https://api.recruitcrm.io/v1/candidates/associated-field/{candidate_slug}/{job_slug}"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            log.error(
                "helpers.fetch_job_specific_fields.failed",
                candidate_slug=candidate_slug,
                job_slug=job_slug,
                status=response.status_code,
            )
            return None
    except requests.exceptions.RequestException as e:
        log.error("helpers.fetch_job_specific_fields.exception", error=str(e))
        return None


def fetch_recruitcrm_assigned_candidates(job_slug, status_id=None):
    """Fetches assigned candidates for a job from RecruitCRM."""
    url = f"https://api.recruitcrm.io/v1/jobs/{job_slug}/assigned-candidates"
    params = {"status_id": status_id} if status_id else {}
    try:
        response = requests.get(
            url, headers=get_recruitcrm_headers(), params=params
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except requests.exceptions.RequestException as e:
        log.error(
            "helpers.fetch_assigned_candidates.failed",
            job_slug=job_slug,
            error=str(e),
        )
        return []


def fetch_alpharun_interview(job_opening_id, interview_id):
    """Fetches interview data from AlphaRun."""
    url = f"https://api.alpharun.com/api/v1/job-openings/{job_opening_id}/interviews/{interview_id}"

    try:
        response = requests.get(url, headers=get_alpharun_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error(
            "helpers.fetch_alpharun_interview.failed",
            interview_id=interview_id,
            error=str(e),
        )
        return None


ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def extract_fireflies_transcript_id(s: str) -> str | None:
    """Parses a string to find a Fireflies transcript ID."""
    if not s:
        return None
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


def fetch_fireflies_transcript(transcript_id: str) -> dict | None:
    """Fetches a transcript from Fireflies.ai using GraphQL."""
    api_key = os.getenv("FIREFLIES_API_KEY")
    if not api_key:
        log.error("helpers.fireflies_api_key_missing")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"query": TRANSCRIPT_QUERY, "variables": {"id": transcript_id}}

    try:
        resp = requests.post(
            GRAPHQL_URL, json=payload, headers=headers, timeout=30
        )
        resp.raise_for_status()
        response_data = resp.json()
        if "errors" in response_data:
            log.error(
                "helpers.fetch_fireflies_transcript.graphql_error",
                transcript_id=transcript_id,
            )
            return None
        return response_data.get("data", {}).get("transcript")
    except requests.exceptions.RequestException as e:
        log.error(
            "helpers.fetch_fireflies_transcript.request_error",
            transcript_id=transcript_id,
            error=str(e),
        )
        return None
    except json.JSONDecodeError:
        log.error(
            "helpers.fetch_fireflies_transcript.json_decode_error",
            transcript_id=transcript_id,
        )
        return None


# ==============================================================================
# 3. DATA PROCESSING & GENERATION HELPERS
# ==============================================================================


def normalise_fireflies_transcript(raw_transcript):
    """Normalises raw Fireflies transcript data."""
    if not raw_transcript:
        return {"metadata": {}, "content": "Not provided."}
    title = raw_transcript.get("title", "N/A")
    sentences = raw_transcript.get("sentences", [])
    content = "\n".join(
        [
            f"{s.get('speaker_name', 'Unknown')}: {s.get('text', '')}"
            for s in sentences
        ]
    )
    return {
        "metadata": {"title": title},
        "content": content or "Transcript content is empty.",
    }


class UnsupportedFileTypeError(Exception):
    """Custom exception for files that cannot be converted."""
    pass


def convert_to_supported_format(
        file_bytes: bytes, original_filename: str
) -> tuple[bytes, str]:
    """
    Checks a file's MIME type and converts it to a supported format if necessary.
    """
    if not magic:
        raise UnsupportedFileTypeError("The 'magic' library is not available for MIME type detection.")

    SUPPORTED_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "text/x-python",
        "application/pdf",
        "image/png",
        "image/jpeg",
    }
    detected_mime_type = magic.from_buffer(file_bytes, mime=True)
    if detected_mime_type in SUPPORTED_MIME_TYPES:
        return file_bytes, detected_mime_type
    if (
            detected_mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        if not docx:
            raise UnsupportedFileTypeError("The 'docx' library is required to process .docx files.")
        try:
            document = docx.Document(io.BytesIO(file_bytes))
            full_text = "\n".join([para.text for para in document.paragraphs])
            return full_text.encode("utf-8"), "text/plain"
        except Exception as e:
            raise UnsupportedFileTypeError(
                f"Failed to convert DOCX file '{original_filename}'. Error: {e}"
            ) from e
    if detected_mime_type == "application/msword":
        raise UnsupportedFileTypeError(
            f"Legacy .doc files are not supported. Please convert '{original_filename}' to DOCX or PDF first."
        )
    raise UnsupportedFileTypeError(
        f"File '{original_filename}' with MIME type '{detected_mime_type}' is not supported."
    )


def upload_resume_to_gemini(resume_info):
    """Downloads a resume, converts it, and uploads it to the Gemini API."""
    if not resume_info:
        return None
    resume_url = resume_info.get("file_link") or resume_info.get("url")
    if not resume_url:
        return None
    try:
        file_response = requests.get(resume_url)
        file_response.raise_for_status()
        original_filename = resume_info.get("filename", "resume.bin")
        converted_bytes, final_mime_type = convert_to_supported_format(
            file_response.content, original_filename
        )
        file_ext = (
            ".txt"
            if final_mime_type == "text/plain"
            else os.path.splitext(original_filename)[1]
        )
        with tempfile.NamedTemporaryFile(
                delete=False, suffix=file_ext
        ) as tmp_file:
            tmp_file.write(converted_bytes)
            tmp_file_path = tmp_file.name
        try:
            gemini_file = genai.upload_file(
                path=tmp_file_path,
                display_name=original_filename,
                mime_type=final_mime_type,
            )
            return gemini_file
        finally:
            os.unlink(tmp_file_path)
    except (requests.exceptions.RequestException, UnsupportedFileTypeError) as e:
        log.error(
            "helpers.upload_resume_to_gemini.failed",
            url=resume_url,
            error=str(e),
        )
        return None
    except Exception as e:
        log.error(
            "helpers.upload_resume_to_gemini.unexpected_error",
            error=str(e),
        )
        return None


def generate_ai_response(model, prompt_parts):
    """Generates a response from the AI model."""
    try:
        response = model.generate_content(prompt_parts)
        return response.text
    except Exception as e:
        log.error("helpers.generate_html_summary.error", error=str(e))
        return None


def generate_html_summary(
        candidate_data,
        job_data,
        interview_data,
        additional_context,
        prompt_type,
        fireflies_data,
        gemini_resume_file,
        model,
):
    """Builds the prompt and generates an HTML summary."""
    candidate_details = candidate_data.get("data", candidate_data)
    job_details = job_data.get("data", job_data)
    interview_details = (
        interview_data.get("data", interview_data) if interview_data else {}
    )

    full_prompt = build_full_prompt(
        prompt_type,
        "single",
        candidate_data=candidate_details,
        job_data=job_details,
        interview_data=interview_details,
        additional_context=additional_context,
        fireflies_data=fireflies_data,
    )

    prompt_parts = [full_prompt]
    if gemini_resume_file:
        prompt_parts.append(gemini_resume_file)

    html_summary = generate_ai_response(model, prompt_parts)

    if html_summary:
        return sub(r"^```(html)?\n|```$", "", html_summary, flags=MULTILINE).strip()
    return None