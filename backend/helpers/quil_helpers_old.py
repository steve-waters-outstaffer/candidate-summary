# helpers/quil_helpers.py

import os
import re
from html.parser import HTMLParser
from typing import Optional, List, Dict, Literal
import structlog
from google import genai
from pydantic import BaseModel

log = structlog.get_logger()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
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
            href = dict(attrs).get('href', '')
            if 'salesq.app' in href:
                self.quil_url = href


class QuilContentValidation(BaseModel):
    """Pydantic model for Gemini's validation of Quil note content"""
    has_interview_content: bool
    reasoning: str


def validate_quil_notes_with_gemini(quil_notes: List[Dict]) -> List[Dict]:
    """
    Use Gemini to filter out Quil notes that don't have actual interview content.
    
    Args:
        quil_notes: List of notes that start with "Quil "
        
    Returns:
        Filtered list of notes that actually contain interview content
    """
    log.info("quil.validate_quil_notes.called", note_count=len(quil_notes))
    
    if not client:
        log.warning("quil.validate_quil_notes.no_client_using_all")
        return quil_notes
    
    if not quil_notes:
        return []
    
    valid_notes = []
    
    for note in quil_notes:
        note_id = note.get('id')
        description = note.get('description', '')
        
        # Quick check - if it has the summary section, likely valid
        if '----Summary----' in description and len(description) > 500:
            valid_notes.append(note)
            log.info("quil.validate_quil_notes.quick_valid", note_id=note_id)
            continue
        
        # Use Gemini to validate
        try:
            preview = description[:1000]  # First 1000 chars
            
            prompt = f"""
Does this Quil interview note contain actual interview content?

Note preview:
{preview}

A valid interview note should have:
- Substantive discussion points or Q&A
- Details about candidate experience, skills, or role fit
- More than just headers/placeholders

Return your analysis.
"""
            
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuilContentValidation
                )
            )
            
            result = QuilContentValidation.model_validate_json(response.text)
            
            log.info("quil.validate_quil_notes.gemini_check",
                     note_id=note_id,
                     has_content=result.has_interview_content,
                     reasoning=result.reasoning)
            
            if result.has_interview_content:
                valid_notes.append(note)
                
        except Exception as e:
            log.error("quil.validate_quil_notes.error", 
                     note_id=note_id, 
                     error=str(e))
            # On error, include the note (fail open)
            valid_notes.append(note)
    
    log.info("quil.validate_quil_notes.complete",
             input_count=len(quil_notes),
             valid_count=len(valid_notes))
    
    return valid_notes



    """Pydantic model for Gemini's note matching response"""
    matched_note_id: int
    confidence: Literal["high", "medium", "low"]
    reasoning: str


def extract_quil_data(note_description: str) -> Optional[Dict]:
    """
    Extract Quil interview data from a RecruitCRM note description.
    
    Args:
        note_description: HTML string from RecruitCRM note
        
    Returns:
        Dict with date, title, summary_html, and quil_url, or None if not a Quil note
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
            'quil_url': parser.quil_url,
            'has_valid_content': bool(summary_match and parser.quil_url)
        }
        
        log.info("quil.extract_quil_data.success", 
                 has_summary=bool(result['summary_html']),
                 has_url=bool(result['quil_url']))
        return result
        
    except Exception as e:
        log.error("quil.extract_quil_data.error", error=str(e))
        return None


def match_quil_note_to_job(
    quil_notes: List[Dict],
    job_title: str,
    job_description: str
) -> Optional[Dict]:
    """
    Use Gemini to match the correct Quil interview note to a job.
    
    Args:
        quil_notes: List of note objects from RecruitCRM
        job_title: Title of the job role
        job_description: Full job description
        
    Returns:
        The matched note dict, or None if matching fails
    """
    log.info("quil.match_quil_note_to_job.called", note_count=len(quil_notes))
    
    if not client:
        log.error("quil.match_quil_note_to_job.no_api_key")
        return quil_notes[0] if quil_notes else None
    
    try:
        # Prepare note previews for Gemini
        notes_preview = []
        for note in quil_notes:
            preview = {
                'id': note['id'],
                'created_on': note['created_on'],
                'description_preview': note['description'][:500]
            }
            # Extract title from description if possible
            if note['description'].startswith('Quil '):
                first_line = note['description'].split('<br/>')[0]
                title_match = re.match(r'Quil \d{1,2}/\d{1,2}/\d{4}: (.+)', first_line)
                if title_match:
                    preview['title'] = title_match.group(1)
            notes_preview.append(preview)
        
        prompt = f"""
Job Title: {job_title}

Job Description:
{job_description[:1000]}

Interview Notes Available ({len(quil_notes)} total):
{notes_preview}

Which note matches THIS specific job? Consider:
- Role title mentioned in note
- Technical requirements discussed
- Client/company name if mentioned
- Date proximity (more recent interviews likely match better)

Return your analysis with the note ID that best matches this job.
"""
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NoteMatchResult
            )
        )
        
        result = NoteMatchResult.model_validate_json(response.text)
        
        log.info("quil.match_quil_note_to_job.gemini_response",
                 matched_id=result.matched_note_id,
                 confidence=result.confidence,
                 reasoning=result.reasoning)
        
        # Find and return the matched note
        for note in quil_notes:
            if note['id'] == result.matched_note_id:
                log.info("quil.match_quil_note_to_job.success", note_id=note['id'])
                return note
        
        # Fallback if ID not found
        log.warning("quil.match_quil_note_to_job.id_not_found", 
                   matched_id=result.matched_note_id)
        return quil_notes[0]
        
    except Exception as e:
        log.error("quil.match_quil_note_to_job.error", error=str(e))
        # Fallback to most recent note
        return quil_notes[0] if quil_notes else None


def get_quil_interview_for_job(
    candidate_notes: List[Dict],
    job_slug: str,
    job_title: str,
    job_description: str
) -> Optional[Dict]:
    """
    Get the Quil interview note that matches a specific job.
    
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
             total_notes=len(candidate_notes))
    
    # STEP 1: Filter for Quil notes only
    quil_notes = [
        note for note in candidate_notes 
        if note.get('description', '').startswith('Quil ')
    ]
    
    if not quil_notes:
        log.info("quil.get_quil_interview_for_job.no_quil_notes")
        return None
    
    log.info("quil.get_quil_interview_for_job.found_quil_notes", 
             count=len(quil_notes))
    
    # STEP 2: Validate ALL Quil notes for actual interview content FIRST
    valid_quil_notes = validate_quil_notes_with_gemini(quil_notes)
    
    if not valid_quil_notes:
        log.warning("quil.get_quil_interview_for_job.no_valid_content")
        return None
    
    log.info("quil.get_quil_interview_for_job.valid_notes_found",
             count=len(valid_quil_notes))
    
    # STEP 3: Among VALID notes, check for manual job association
    for note in valid_quil_notes:
        associated_jobs = note.get('associated_jobs', [])
        if job_slug in associated_jobs:
            log.info("quil.get_quil_interview_for_job.manual_match_found",
                     note_id=note['id'])
            return extract_quil_data(note['description'])
    
    # STEP 4: If no manual association found, use Gemini to match by content
    log.info("quil.get_quil_interview_for_job.using_gemini_match")
    matched_note = match_quil_note_to_job(valid_quil_notes, job_title, job_description)
    
    if matched_note:
        return extract_quil_data(matched_note['description'])
    
    log.warning("quil.get_quil_interview_for_job.no_match_found")
    return None
