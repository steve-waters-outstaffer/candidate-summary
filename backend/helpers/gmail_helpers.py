# helpers/gmail_helpers.py
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import structlog
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from xhtml2pdf import pisa
from io import BytesIO

log = structlog.get_logger()

def create_gmail_draft(user_access_token, subject, html_body, to_email=None, refresh_token=None, client_id=None, client_secret=None, summary_html=None, pdf_filename=None):
    """
    Creates a Gmail draft using the user's OAuth access token.
    
    Args:
        user_access_token (str): User's Google OAuth access token
        subject (str): Email subject line
        html_body (str): HTML content for email body
        to_email (str): Optional recipient email (leave blank if user should fill)
        refresh_token (str): Optional refresh token for automatic token refresh
        client_id (str): Optional OAuth client ID
        client_secret (str): Optional OAuth client secret
        summary_html (str): Optional HTML summary to convert to PDF and attach
        pdf_filename (str): Optional PDF filename
    
    Returns:
        dict: {'success': bool, 'draft_id': str, 'draft_url': str} or error
    """
    try:
        # Generate PDF from summary_html if provided
        attachment_data = None
        if summary_html and pdf_filename:
            try:
                pdf_buffer = BytesIO()
                pisa_status = pisa.CreatePDF(summary_html, dest=pdf_buffer)
                if not pisa_status.err:
                    attachment_data = pdf_buffer.getvalue()
                    log.info("gmail.pdf.generated", filename=pdf_filename)
                else:
                    log.error("gmail.pdf.generation_failed", error="pisa error")
            except Exception as pdf_error:
                log.error("gmail.pdf.generation_failed", error=str(pdf_error))
                # Continue without PDF - we'll create draft anyway
        
        # Build credentials with refresh capability if refresh_token provided
        if refresh_token and client_id and client_secret:
            credentials = Credentials(
                token=user_access_token,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret
            )
        else:
            # Fallback to basic credentials (will fail on token expiry)
            credentials = Credentials(token=user_access_token)
        
        # Build Gmail API service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Create message with or without attachment
        if attachment_data and pdf_filename:
            # Create multipart message with attachment
            message = MIMEMultipart()
            message['subject'] = subject
            if to_email:
                message['to'] = to_email
            
            # Add HTML body
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
            
            # Add PDF attachment
            pdf_part = MIMEApplication(attachment_data, _subtype='pdf')
            pdf_part.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            message.attach(pdf_part)
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        else:
            # Simple message without attachment
            message = MIMEText(html_body, 'html')
            message['subject'] = subject
            if to_email:
                message['to'] = to_email
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Create draft
        draft_body = {
            'message': {
                'raw': raw_message
            }
        }
        
        draft = service.users().drafts().create(
            userId='me',
            body=draft_body
        ).execute()
        
        draft_id = draft['id']
        draft_url = f"https://mail.google.com/mail/u/0/#drafts?compose={draft_id}"
        
        log.info("gmail.draft.created", draft_id=draft_id, has_attachment=bool(attachment_data))
        
        return {
            'success': True,
            'draft_id': draft_id,
            'draft_url': draft_url,
            'new_access_token': credentials.token if credentials.token != user_access_token else None,
            'pdf_generated': bool(attachment_data)
        }
        
    except Exception as e:
        log.error("gmail.draft.error", error=str(e))
        return {
            'success': False,
            'error': str(e)
        }
