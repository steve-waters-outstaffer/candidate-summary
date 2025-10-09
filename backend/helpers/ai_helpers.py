# helpers/ai_helpers.py
import structlog

# --- Start Debugging Imports ---
log = structlog.get_logger()
log.info("helpers.ai_helpers: Top of file, starting imports.")

try:
    log.info("helpers.ai_helpers: Importing os...")
    import os
    log.info("helpers.ai_helpers: Importing io...")
    import io
    log.info("helpers.ai_helpers: Importing tempfile...")
    import tempfile
    log.info("helpers.ai_helpers: Importing re...")
    from re import sub, MULTILINE
    log.info("helpers.ai_helpers: Importing requests...")
    import requests

    log.info("helpers.ai_helpers: Importing google.genai...")
    import google.genai as genai
    log.info("helpers.ai_helpers: Successfully imported google.genai.")

    log.info("helpers.ai_helpers: Importing from config.prompts...")
    from config.prompts import build_full_prompt
    log.info("helpers.ai_helpers: Successfully imported from config.prompts.")

    log.info("helpers.ai_helpers: Importing magic...")
    try:
        import filetype # Reverting to original import
        log.info("helpers.ai_helpers: Successfully imported filetype.")
    except ImportError:
        log.error("The 'filetype' library is not installed.")
        filetype = None

    log.info("helpers.ai_helpers: Importing docx...")
    try:
        import docx
        log.info("helpers.ai_helpers: Successfully imported docx.")
    except ImportError:
        log.error("The 'python-docx' library is not installed.")
        docx = None

    log.info("helpers.ai_helpers: All imports successful.")

except Exception as e:
    log.error("helpers.ai_helpers: FAILED during import", error=str(e), exc_info=True)
    import sys
    sys.exit(1)
# --- End Debugging Imports ---


class UnsupportedFileTypeError(Exception):
    """Custom exception for files that cannot be converted."""
    pass

def convert_to_supported_format(file_bytes: bytes, original_filename: str) -> tuple[bytes, str]:
    """Checks and converts a file to a supported format for Gemini."""
    if not filetype:
        raise UnsupportedFileTypeError("The 'filetype' library is not available for MIME type detection.")

    SUPPORTED_MIME_TYPES = {'text/plain', 'application/pdf', 'image/png', 'image/jpeg'}

    kind = filetype.guess(file_bytes)
    if kind is None:
        log.warning("mime_type_detection_failed", reason="Cannot guess file type")
        detected_mime_type = 'application/octet-stream'
    else:
        detected_mime_type = kind.mime

    log.info("mime_type_detected", mime_type=detected_mime_type)


    if detected_mime_type in SUPPORTED_MIME_TYPES:
        return file_bytes, detected_mime_type

    if detected_mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        if not docx:
            raise UnsupportedFileTypeError("python-docx is required to process .docx files.")
        try:
            document = docx.Document(io.BytesIO(file_bytes))
            full_text = "\n".join([para.text for para in document.paragraphs])
            return full_text.encode('utf-8'), 'text/plain'
        except Exception as e:
            raise UnsupportedFileTypeError(f"Failed to convert DOCX file '{original_filename}'.") from e

    raise UnsupportedFileTypeError(f"File type '{detected_mime_type}' is not supported.")

def upload_resume_to_gemini(resume_info, client):
    """Downloads, converts, and uploads a resume to the Gemini API."""
    if not resume_info: return None
    resume_url = resume_info.get('file_link') or resume_info.get('url')
    if not resume_url: return None

    try:
        file_response = requests.get(resume_url)
        file_response.raise_for_status()
        original_filename = resume_info.get('filename', 'resume.bin')

        converted_bytes, final_mime_type = convert_to_supported_format(
            file_response.content, original_filename
        )

        # Use proper file extension based on MIME type so Gemini can detect it correctly
        extension_map = {
            'text/plain': '.txt',
            'application/pdf': '.pdf',
            'image/png': '.png',
            'image/jpeg': '.jpg'
        }
        file_extension = extension_map.get(final_mime_type, '.bin')

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(converted_bytes)
            tmp_file_path = tmp_file.name

        try:
            gemini_file = client.files.upload(file=tmp_file_path)
            log.info("ai.upload_resume.success", file_name=gemini_file.name, state=gemini_file.state, detected_mime=gemini_file.mime_type)
            
            # Wait for file to be processed (CRITICAL for PDFs)
            import time
            max_wait = 60
            start_time = time.time()
            
            while gemini_file.state == 'PROCESSING':
                if time.time() - start_time > max_wait:
                    log.error("ai.upload_resume.timeout", file_name=gemini_file.name)
                    return None
                    
                time.sleep(2)
                gemini_file = client.files.get(name=gemini_file.name)
                log.info("ai.upload_resume.processing", file_name=gemini_file.name, state=gemini_file.state)
            
            if gemini_file.state == 'FAILED':
                log.error("ai.upload_resume.failed_state", file_name=gemini_file.name)
                return None
            
            log.info("ai.upload_resume.ready", file_name=gemini_file.name, state=gemini_file.state, detected_mime=gemini_file.mime_type)
            return gemini_file
            
        finally:
            os.unlink(tmp_file_path)

    except (requests.exceptions.RequestException, UnsupportedFileTypeError) as e:
        log.error("ai.upload_resume.failed", url=resume_url, error=str(e))
        return None
    except Exception as e:
        log.error("ai.upload_resume.unexpected_error", error=str(e))
        return None

def generate_ai_response(client, prompt_parts):
    """Generates a response from the AI model."""
    try:
        log.info("ai.generate_response.called", num_parts=len(prompt_parts))
        
        # Debug: log what we're actually sending
        for i, part in enumerate(prompt_parts):
            part_type = type(part).__name__
            if hasattr(part, 'name'):
                log.info(f"ai.generate_response.part_{i}", type=part_type, name=part.name)
            else:
                log.info(f"ai.generate_response.part_{i}", type=part_type, preview=str(part)[:100])
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-09-2025',
            contents=prompt_parts
        )
        log.info("ai.generate_response.success")
        return response.text
    except Exception as e:
        log.error("ai.generate_response.error", error=str(e), error_type=type(e).__name__)
        # Try to extract more details from the exception
        if hasattr(e, 'response'):
            log.error("ai.generate_response.response_details", response=str(e.response))
        return None

def generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data, gemini_resume_file, client):
    """Builds the full prompt and generates an HTML summary using the AI model."""
    full_prompt = build_full_prompt(
        prompt_type,
        "single",
        candidate_data=candidate_data.get('data', candidate_data),
        job_data=job_data.get('data', job_data),
        interview_data=interview_data.get('data', interview_data) if interview_data else {},
        additional_context=additional_context,
        fireflies_data=fireflies_data
    )
    
    # With the new google-genai SDK, files and text should be passed as separate items in a list
    # The SDK will handle the proper formatting internally
    contents = []
    contents.append({"role": "user", "parts": [{"text": full_prompt}]})
    
    if gemini_resume_file:
        # Add the file as a part using the file URI
        contents[0]["parts"].append({"file_data": {"file_uri": gemini_resume_file.uri}})

    html_summary = generate_ai_response(client, contents)
    if html_summary:
        return sub(r'^```(html)?\n|```$', '', html_summary, flags=MULTILINE).strip()
    return html_summary