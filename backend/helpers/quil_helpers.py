# helpers/quil_helpers.py
# Renamed internally to corecruit — keeping filename for deployment compatibility.

import os
import re
import socket
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


class CorecruitLinkParser(HTMLParser):
    """HTML parser to extract CoRecruit meeting links from note descriptions"""
    def __init__(self):
        super().__init__()
        self.corecruit_url = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and 'app.corecruit.com' in value:
                    self.corecruit_url = value


class CorecruitNoteSelection(BaseModel):
    """Pydantic model for Gemini's selection of the best CoRecruit interview note"""
    selected_note_id: Optional[int] = None
    has_valid_interview: bool
    reasoning: str


def extract_corecruit_data(note_description: str) -> Optional[Dict]:
    """
    Extract CoRecruit interview data from a RecruitCRM note description.

    Args:
        note_description: HTML string from RecruitCRM note

    Returns:
        Dict with date, title, summary_html, and quil_link (kept for prompt template compatibility)
    """
    log.info("corecruit.extract_data.called")

    if not note_description or not note_description.startswith('CoRecruit '):
        log.info("corecruit.extract_data.not_corecruit_note")
        return None

    try:
        first_line = note_description.split('<br/>')[0] if '<br/>' in note_description else note_description.split('\n')[0]
        header_match = re.match(r'CoRecruit (\d{1,2}/\d{1,2}/\d{4}): (.+)', first_line)

        summary_match = re.search(
            r'<b>----Summary----</b>(.*?)<b>----Manual Notes----</b>',
            note_description,
            re.DOTALL
        )

        parser = CorecruitLinkParser()
        parser.feed(note_description)
        corecruit_url = parser.corecruit_url

        if not corecruit_url:
            url_match = re.search(r'https://app\.corecruit\.com/\S+', note_description)
            if url_match:
                corecruit_url = url_match.group(0)

        result = {
            'date': header_match.group(1) if header_match else None,
            'title': header_match.group(2).strip() if header_match else None,
            'summary_html': summary_match.group(1).strip() if summary_match else None,
            'quil_link': corecruit_url  # key kept for backwards compatibility with prompt templates
        }

        log.info("corecruit.extract_data.success",
                 has_summary=bool(result['summary_html']),
                 has_url=bool(result['quil_link']))
        return result

    except Exception as e:
        log.error("corecruit.extract_data.error", error=str(e))
        return None


def select_best_corecruit_note_with_gemini(
    corecruit_notes: List[Dict],
    job_slug: str,
    job_title: str,
    job_description: str,
    model: str = 'gemini-3-flash-preview'
) -> Optional[Dict]:
    """
    Use Gemini to select the best CoRecruit interview note for a job.
    Does both content validation AND job matching in one call.
    """
    log.info("corecruit.select_best_note.called",
             note_count=len(corecruit_notes),
             job_slug=job_slug)

    if not client:
        log.warning("corecruit.select_best_note.no_client")
        for note in corecruit_notes:
            if job_slug in note.get('associated_jobs', []):
                log.info("corecruit.select_best_note.fallback_found_associated")
                return note
        log.info("corecruit.select_best_note.fallback_returning_first")
        return corecruit_notes[0] if corecruit_notes else None

    if not corecruit_notes:
        return None

    try:
        log.info("corecruit.select_best_note.preparing_gemini_request", note_count=len(corecruit_notes))

        notes_data = []
        for note in corecruit_notes:
            note_info = {
                'id': note['id'],
                'created_on': note.get('created_on'),
                'description_preview': note['description'][:800],
                'is_manually_associated': job_slug in note.get('associated_jobs', [])
            }
            if note['description'].startswith('CoRecruit '):
                first_line = note['description'].split('<br/>')[0]
                title_match = re.match(r'CoRecruit \d{1,2}/\d{1,2}/\d{4}: (.+)', first_line)
                if title_match:
                    note_info['title'] = title_match.group(1)
            notes_data.append(note_info)

        log.info("corecruit.select_best_note.calling_gemini", notes_prepared=len(notes_data))

        prompt = f"""
You are analyzing CoRecruit meeting notes to find the best interview note for a specific job.

**Job Details:**
Title: {job_title}
Description: {job_description[:1000]}

**Available CoRecruit Notes ({len(corecruit_notes)} total):**
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

        log.info("corecruit.select_best_note.sending_to_gemini")

        import socket
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)

        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CorecruitNoteSelection
                )
            )
        finally:
            socket.setdefaulttimeout(old_timeout)

        log.info("corecruit.select_best_note.gemini_responded")

        result = CorecruitNoteSelection.model_validate_json(response.text)

        log.info("corecruit.select_best_note.gemini_response",
                 selected_id=result.selected_note_id,
                 has_valid=result.has_valid_interview,
                 reasoning=result.reasoning)

        if not result.has_valid_interview or result.selected_note_id is None:
            log.info("corecruit.select_best_note.no_valid_interview")
            return None

        for note in corecruit_notes:
            if note['id'] == result.selected_note_id:
                log.info("corecruit.select_best_note.success", note_id=note['id'])
                return note

        log.warning("corecruit.select_best_note.id_not_found",
                    selected_id=result.selected_note_id)
        return None

    except Exception as e:
        log.error("corecruit.select_best_note.error", error=str(e))
        for note in corecruit_notes:
            if job_slug in note.get('associated_jobs', []):
                return note
        return corecruit_notes[0] if corecruit_notes else None


def get_corecruit_interview_for_job(
    candidate_notes: List[Dict],
    job_slug: str,
    job_title: str,
    job_description: str,
    model: str = 'gemini-3-flash-preview'
) -> Optional[Dict]:
    """
    Get the CoRecruit interview note that best matches a specific job.
    Uses ONE Gemini call to both validate content and match to job.
    """
    log.info("corecruit.get_interview_for_job.called",
             job_slug=job_slug,
             total_notes=len(candidate_notes),
             candidate_notes_type=type(candidate_notes).__name__)

    corecruit_notes = [
        note for note in candidate_notes
        if note.get('description', '').startswith('CoRecruit ')
    ]

    log.info("corecruit.get_interview_for_job.filtered",
             corecruit_notes_count=len(corecruit_notes))

    if not corecruit_notes:
        log.info("corecruit.get_interview_for_job.no_corecruit_notes")
        return None

    log.info("corecruit.get_interview_for_job.found_notes", count=len(corecruit_notes))
    log.info("corecruit.get_interview_for_job.calling_gemini")

    best_note = select_best_corecruit_note_with_gemini(
        corecruit_notes,
        job_slug,
        job_title,
        job_description,
        model=model
    )

    if best_note:
        extracted = extract_corecruit_data(best_note['description'])
        if extracted:
            log.info("corecruit.get_interview_for_job.success")
            return extracted

    log.info("corecruit.get_interview_for_job.no_valid_interview")
    return None
