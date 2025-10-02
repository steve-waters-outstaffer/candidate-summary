# helpers/gmail_helpers.py
import base64
from email.mime.text import MIMEText
import structlog
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

log = structlog.get_logger()

def create_gmail_draft(user_access_token, subject, html_body, to_email=None):
    """
    Creates a Gmail draft using the user's OAuth access token.
    
    Args:
        user_access_token (str): User's Google OAuth access token
        subject (str): Email subject line
        html_body (str): HTML content for email body
        to_email (str): Optional recipient email (leave blank if user should fill)
    
    Returns:
        dict: {'success': bool, 'draft_id': str, 'draft_url': str} or error
    """
    try:
        # Build credentials from access token
        credentials = Credentials(token=user_access_token)
        
        # Build Gmail API service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Create message
        message = MIMEText(html_body, 'html')
        message['subject'] = subject
        if to_email:
            message['to'] = to_email
        
        # Encode message
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
        
        log.info("gmail.draft.created", draft_id=draft_id)
        
        return {
            'success': True,
            'draft_id': draft_id,
            'draft_url': draft_url
        }
        
    except Exception as e:
        log.error("gmail.draft.error", error=str(e))
        return {
            'success': False,
            'error': str(e)
        }
