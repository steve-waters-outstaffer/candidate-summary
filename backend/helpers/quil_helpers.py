# helpers/quil_helpers.py

import os
import re
from html.parser import HTMLParser
from typing import Optional, List, Dict
import structlog
from google import genai
from pydantic import BaseModel

log = structlog.get_logger()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


class QuilLinkParser(HTMLParser):
    """HTML parser to extract Quil meeting links from note descriptions"""
    def __init__(self):
        super().__init__()
        self.quil_url = None
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and 'salesq.app' in value:
                    self.quil_url = value


class QuilNoteSelection(BaseModel):
    """Pydantic model for Gemini's selection of the best Quil interview note"""
    selected_note_id: Optional[int] = None
    has_valid_interview: bool
    reasoning: str


def extract_quil_data(note_description: str) -> Optional[Dict]:
    """
    Extract Quil interview data from a RecruitCRM note description.
    
    Args:
        note_description: HTML string from RecruitCRM note
        
    Returns:
        Dict with date, title, summary_html, and quil_url
    """
    log.info("quil.extract_quil_data.called")
    
    if not note_description or not note_description.startswith('Quil '):
        log.info("quil.extract_quil_data.not_quil_note")
        return None
    
    try:
        # Extract date and title from first line
        first_line = note_description.split('<br/>')[0] if '<br/>' in note_description else note_description.split('\n')[0]
        header_match = re.match(r'Quil (\d{1,2}/\d{1,2}/\d{4}): (.+)', first_line)
        
        # Extract summary content between markers
        summary_match = re.search(
            r'<b>----Summary----</b>(.*?)<b>----Manual Notes----</b>',
            note_description,
            re.DOTALL
        )
        
        # Extract Quil URL
        parser = QuilLinkParser()
        parser.feed(note_description)
        
        result = {
            'date': header_match.group(1) if header_match else None,
            'title': header_match.group(2).strip() if header_match else None,
            'summary_html': summary_match.group(1).strip() if summary_match else None,
            'quil_link': parser.quil_url
        }
        
        log.info("quil.extract_quil_data.success", 
                 has_summary=bool(result['summary_html']),
                 has_url=bool(result['quil_link']))
        return result
        
    except Exception as e:
        log.error("quil.extract_quil_data.error", error=str(e))
        return None


def select_best_quil_note_with_gemini(
    quil_notes: List[Dict],
    job_slug: str,
    job_title: str,
    job_description: str
) -> Optional[Dict]:
    """
    Use Gemini to select the best Quil interview note for a job.
    Does both content validation AND job matching in one call.
    
    Args:
        quil_notes: List of Quil notes from RecruitCRM
        job_slug: RecruitCRM job slug
        job_title: Title of the job
        job_description: Full job description
        
    Returns:
        The best matching note dict, or None if no valid interview found
    """
    log.info("quil.select_best_note.called", 
             note_count=len(quil_notes),
             job_slug=job_slug)
    
    if not client:
        log.warning("quil.select_best_note.no_client")
        # Fallback: return first note with job association, or just first note
        for note in quil_notes:
            if job_slug in note.get('associated_jobs', []):
                log.info("quil.select_best_note.fallback_found_associated")
                return note
        log.info("quil.select_best_note.fallback_returning_first")
        return quil_notes[0] if quil_notes else None
    
    if not quil_notes:
        return None
    
    try:
        log.info("quil.select_best_note.preparing_gemini_request", note_count=len(quil_notes))
        
        # Prepare note summaries for Gemini
        notes_data = []
        for note in quil_notes:
            note_info = {
                'id': note['id'],
                'created_on': note.get('created_on'),
                'description_preview': note['description'][:800],  # First 800 chars
                'is_manually_associated': job_slug in note.get('associated_jobs', [])
            }
            
            # Extract title from description if possible
            if note['description'].startswith('Quil '):
                first_line = note['description'].split('<br/>')[0]
                title_match = re.match(r'Quil \d{1,2}/\d{1,2}/\d{4}: (.+)', first_line)
                if title_match:
                    note_info['title'] = title_match.group(1)
            
            notes_data.append(note_info)
        
        log.info("quil.select_best_note.calling_gemini", notes_prepared=len(notes_data))
        
        prompt = f"""
You are analyzing Quil meeting notes to find the best interview note for a specific job.

**Job Details:**
Title: {job_title}
Description: {job_description[:1000]}

**Available Quil Notes ({len(quil_notes)} total):**
{notes_data}

**Your Task:**
1. Identify which note (if any) contains a REAL INTERVIEW with substantive content
   - Must have discussion points, Q&A, details about candidate experience/skills
   - NOT just call logs, empty placeholders, or brief check-ins
   
2. If multiple valid interviews exist, pick the one that best matches THIS job:
   - Consider role title mentioned
   - Technical requirements discussed
   - Date proximity (more recent is better)
   - Manual job association (is_manually_associated=true is a strong signal)

**Return:**
- selected_note_id: The ID of the best interview note, or null if none are valid
- has_valid_interview: true only if you found a real interview with content
- reasoning: Brief explanation of your decision

If no notes contain actual interview content, return has_valid_interview=false and selected_note_id=null.
"""
        
        log.info("quil.select_best_note.sending_to_gemini")
        
        # Add timeout to prevent hanging
        import socket
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)  # 30 second timeout
        
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuilNoteSelection
                )
            )
        finally:
            socket.setdefaulttimeout(old_timeout)
        
        log.info("quil.select_best_note.gemini_responded")
        
        result = QuilNoteSelection.model_validate_json(response.text)
        
        log.info("quil.select_best_note.gemini_response",
                 selected_id=result.selected_note_id,
                 has_valid=result.has_valid_interview,
                 reasoning=result.reasoning)
        
        if not result.has_valid_interview or result.selected_note_id is None:
            log.info("quil.select_best_note.no_valid_interview")
            return None
        
        # Find and return the selected note
        for note in quil_notes:
            if note['id'] == result.selected_note_id:
                log.info("quil.select_best_note.success", note_id=note['id'])
                return note
        
        # Fallback if ID not found
        log.warning("quil.select_best_note.id_not_found", 
                   selected_id=result.selected_note_id)
        return None
        
    except Exception as e:
        log.error("quil.select_best_note.error", error=str(e))
        # Fallback: return first note with job association
        for note in quil_notes:
            if job_slug in note.get('associated_jobs', []):
                return note
        return quil_notes[0] if quil_notes else None


def get_quil_interview_for_job(
    candidate_notes: List[Dict],
    job_slug: str,
    job_title: str,
    job_description: str
) -> Optional[Dict]:
    """
    Get the Quil interview note that matches a specific job.
    
    Uses ONE Gemini call to both validate content and match to job.
    
    Args:
        candidate_notes: All notes from RecruitCRM for this candidate
        job_slug: RecruitCRM job slug
        job_title: Title of the job
        job_description: Full job description
        
    Returns:
        Dict with extracted Quil data, or None if no matching note found
    """
    log.info("quil.get_quil_interview_for_job.called", 
             job_slug=job_slug,
             total_notes=len(candidate_notes),
             candidate_notes_type=type(candidate_notes).__name__)
    
    # Filter for Quil notes only
    quil_notes = [
        note for note in candidate_notes 
        if note.get('description', '').startswith('Quil ')
    ]
    
    log.info("quil.get_quil_interview_for_job.filtered",
             quil_notes_count=len(quil_notes),
             quil_notes_type=type(quil_notes).__name__)
    
    if not quil_notes:
        log.info("quil.get_quil_interview_for_job.no_quil_notes")
        return None
    
    log.info("quil.get_quil_interview_for_job.found_quil_notes", 
             count=len(quil_notes))
    
    # Use ONE Gemini call to validate and select best note
    log.info("quil.get_quil_interview_for_job.calling_gemini")
    best_note = select_best_quil_note_with_gemini(
        quil_notes, 
        job_slug, 
        job_title, 
        job_description
    )
    
    log.info("quil.get_quil_interview_for_job.gemini_returned",
             best_note_type=type(best_note).__name__ if best_note else "None")
    
    if not best_note:
        log.warning("quil.get_quil_interview_for_job.no_match_found")
        return None
    
    # Extract and return the data
    log.info("quil.get_quil_interview_for_job.extracting_data",
             best_note_has_description=('description' in best_note) if isinstance(best_note, dict) else False)
    return extract_quil_data(best_note['description'])
