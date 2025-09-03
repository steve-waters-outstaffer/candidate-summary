import io
import mimetypes
import docx # From python-docx library
import structlog

log = structlog.get_logger()

# A set of MIME types that the Gemini API is known to support for file uploads.
# This list can be expanded based on the official Gemini documentation.
SUPPORTED_MIME_TYPES = {
    'text/plain',
    'text/markdown',
    'text/x-python',
    'application/pdf',
    'image/png',
    'image/jpeg',
    # Add other supported types as needed
}

class UnsupportedFileTypeError(Exception):
    """Custom exception for files that cannot be converted."""
    pass

def convert_to_supported_format(file_bytes: bytes, original_filename: str) -> tuple[bytes, str]:
    """
    Checks a file's MIME type and converts it to a supported format if necessary.

    Args:
        file_bytes: The content of the file as bytes.
        original_filename: The original name of the file, used to guess MIME type.

    Returns:
        A tuple containing the (potentially converted) file bytes and the
        new, supported MIME type for the Gemini API.

    Raises:
        UnsupportedFileTypeError: If the file type is not supported and cannot be converted.
    """
    # Guess the original MIME type from the filename
    original_mime_type, _ = mimetypes.guess_type(original_filename)
    if not original_mime_type:
        original_mime_type = 'application/octet-stream' # Default for unknown types

    # If the file is already in a supported format, return it as is.
    if original_mime_type in SUPPORTED_MIME_TYPES:
        log.info(
            "file_converter.format.supported",
            filename=original_filename,
            mime_type=original_mime_type,
        )
        return file_bytes, original_mime_type

    # --- Conversion Logic ---

    # Handle .docx files -> convert to plain text
    if original_mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        log.info(
            "file_converter.conversion.started",
            filename=original_filename,
            from_format="docx",
            to_format="text/plain",
        )
        try:
            document = docx.Document(io.BytesIO(file_bytes))
            full_text = "\n".join([para.text for para in document.paragraphs])
            converted_bytes = full_text.encode('utf-8')
            return converted_bytes, 'text/plain'
        except Exception as e:
            raise UnsupportedFileTypeError(
                f"Failed to convert DOCX file '{original_filename}'. Error: {e}"
            ) from e

    # Handle legacy .doc files -> explicitly not supported
    if original_mime_type == 'application/msword':
        raise UnsupportedFileTypeError(
            f"Legacy .doc files are not supported. Please convert '{original_filename}' to DOCX or PDF first."
        )

    # If we reach here, the file type is not supported and we have no converter for it.
    raise UnsupportedFileTypeError(
        f"File '{original_filename}' with MIME type '{original_mime_type}' is not supported for upload."
    )
