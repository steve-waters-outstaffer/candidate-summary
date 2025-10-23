# helpers/pdf_helpers.py
import io
import structlog
from weasyprint import HTML

log = structlog.get_logger()

def generate_pdf_from_html(html_content, candidate_name, job_name):
    """
    Generate a PDF from HTML content.
    
    Args:
        html_content (str): HTML string to convert to PDF
        candidate_name (str): Candidate name for filename
        job_name (str): Job name for filename
    
    Returns:
        tuple: (pdf_bytes, filename) or (None, None) if failed
    """
    try:
        # Clean up names for filename
        safe_candidate = candidate_name.replace(' ', '_').replace('/', '_')
        safe_job = job_name.replace(' ', '_').replace('/', '_')
        filename = f"{safe_candidate}-{safe_job}.pdf"
        
        # Generate PDF from HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        log.info("pdf.generated", filename=filename, size=len(pdf_bytes))
        return pdf_bytes, filename
        
    except Exception as e:
        log.error("pdf.generation.failed", error=str(e))
        return None, None
