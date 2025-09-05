# helpers/ai_helpers.py
import structlog

import io
import os
import tempfile
from re import sub, MULTILINE
import google.generativeai as genai
import requests
from config.prompts import build_full_prompt

# Import optional libraries
try:
    import magic
except ImportError:
    magic = None

try:
    import docx
except ImportError:
    docx = None


log = structlog.get_logger()


class UnsupportedFileTypeError(Exception):
    """Custom exception for files that cannot be converted."""
    pass

def convert_to_supported_format(file_bytes: bytes, original_filename: str) -> tuple[bytes, str]:
    """Checks and converts a file to a supported format for Gemini."""
    log.info("ai.convert_to_supported_format.called", original_filename=original_filename)
    if not magic:
        raise UnsupportedFileTypeError("The 'magic' library is not available for MIME type detection.")

    SUPPORTED_MIME_TYPES = {'text/plain', 'application/pdf', 'image/png', 'image/jpeg'}
    detected_mime_type = magic.from_buffer(file_bytes, mime=True)
    log.info("ai.convert_to_supported_format.detected_mime_type", mime_type=detected_mime_type)

    if detected_mime_type in SUPPORTED_MIME_TYPES:
        return file_bytes, detected_mime_type

    if detected_mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        if not docx:
            raise UnsupportedFileTypeError("python-docx is required to process .docx files.")
        try:
            log.info("ai.convert_to_supported_format.converting_docx")
            document = docx.Document(io.BytesIO(file_bytes))
            full_text = "\n".join([para.text for para in document.paragraphs])
            return full_text.encode('utf-8'), 'text/plain'
        except Exception as e:
            raise UnsupportedFileTypeError(f"Failed to convert DOCX file '{original_filename}'.") from e

    raise UnsupportedFileTypeError(f"File type '{detected_mime_type}' is not supported.")

def upload_resume_to_gemini(resume_info):
    """Downloads, converts, and uploads a resume to the Gemini API."""
    log.info("ai.upload_resume_to_gemini.called")
    if not resume_info: return None
    resume_url = resume_info.get('file_link') or resume_info.get('url')
    if not resume_url: return None

    original_filename = resume_info.get('filename', 'resume.bin')
    log.info("ai.upload_resume_to_gemini.processing", resume_url=resume_url, original_filename=original_filename)

    try:
        file_response = requests.get(resume_url)
        file_response.raise_for_status()

        converted_bytes, final_mime_type = convert_to_supported_format(
            file_response.content, original_filename
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp_file:
            tmp_file.write(converted_bytes)
            tmp_file_path = tmp_file.name

        try:
            log.info("ai.upload_resume_to_gemini.uploading_to_gemini", file_path=tmp_file_path, mime_type=final_mime_type)
            gemini_file = genai.upload_file(
                path=tmp_file_path,
                display_name=original_filename,
                mime_type=final_mime_type
            )
            log.info("ai.upload_resume_to_gemini.upload_successful", gemini_file_name=gemini_file.name)
            return gemini_file
        finally:
            os.unlink(tmp_file_path)

    except (requests.exceptions.RequestException, UnsupportedFileTypeError) as e:
        log.error("ai.upload_resume.failed", url=resume_url, error=str(e))
        return None
    except Exception as e:
        log.error("ai.upload_resume.unexpected_error", error=str(e))
        return None

def generate_ai_response(model, prompt_parts):
    """Generates a response from the AI model."""
    log.info("ai.generate_ai_response.called")
    try:
        response = model.generate_content(prompt_parts)
        log.info("ai.generate_ai_response.success")
        return response.text
    except Exception as e:
        log.error("ai.generate_response.error", error=str(e))
        return None

def generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data, gemini_resume_file, model):
    """Builds the full prompt and generates an HTML summary using the AI model."""
    log.info("ai.generate_html_summary.called", prompt_type=prompt_type, has_interview=interview_data is not None, has_fireflies=fireflies_data is not None, has_resume=gemini_resume_file is not None)
    full_prompt = build_full_prompt(
        prompt_type,
        "single",
        candidate_data=candidate_data.get('data', candidate_data),
        job_data=job_data.get('data', job_data),
        interview_data=interview_data.get('data', interview_data) if interview_data else {},
        additional_context=additional_context,
        fireflies_data=fireflies_data
    )
    prompt_parts = [full_prompt]
    if gemini_resume_file:
        prompt_parts.append(gemini_resume_file)

    html_summary = generate_ai_response(model, prompt_parts)
    if html_summary:
        return sub(r'^```(html)?\n|```$', '', html_summary, flags=MULTILINE).strip()
    return html_summary