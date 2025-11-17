# helpers/recruitcrm_helpers.py
import os
import requests
import structlog
import datetime

log = structlog.get_logger()

RECRUITCRM_API_KEY = os.getenv('RECRUITCRM_API_KEY')
ALPHARUN_API_KEY = os.getenv('ALPHARUN_API_KEY')

def get_recruitcrm_headers():
    """Returns the authorization headers for the RecruitCRM API."""
    log.info("recruitcrm.get_recruitcrm_headers.called")
    if not RECRUITCRM_API_KEY:
        raise ValueError("RECRUITCRM_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {RECRUITCRM_API_KEY}',
        'Accept': 'application/json'
    }



def get_alpharun_headers():
    """Returns the authorization headers for the AlphaRun API."""
    log.info("recruitcrm.get_alpharun_headers.called")
    if not ALPHARUN_API_KEY:
        raise ValueError("ALPHARUN_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {ALPHARUN_API_KEY}',
        'Content-Type': 'application/json'
    }

def fetch_recruitcrm_candidate(slug):
    """Fetches candidate data from RecruitCRM using the candidate's slug."""
    log.info("recruitcrm.fetch_recruitcrm_candidate.called", slug=slug)
    url = f'https://api.recruitcrm.io/v1/candidates/{slug}'
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        log.info("recruitcrm.fetch_recruitcrm_candidate.success", slug=slug)
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_candidate.failed", slug=slug, error=str(e))
        return None

def fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug):
    """Fetches job-specific custom fields for a candidate from RecruitCRM."""
    log.info("recruitcrm.fetch_recruitcrm_candidate_job_specific_fields.called", candidate_slug=candidate_slug, job_slug=job_slug)
    url = f"https://api.recruitcrm.io/v1/candidates/associated-field/{candidate_slug}/{job_slug}"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        if response.status_code == 200:
            log.info("recruitcrm.fetch_job_specific_fields.success", candidate_slug=candidate_slug, job_slug=job_slug)
            return response.json().get('data', {})
        else:
            log.error(
                "recruitcrm.fetch_job_specific_fields.failed",
                status=response.status_code,
                candidate_slug=candidate_slug,
                job_slug=job_slug
            )
            return None
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_job_specific_fields.exception", error=str(e), candidate_slug=candidate_slug, job_slug=job_slug)
        return None

def fetch_candidate_interview_id(candidate_slug, job_slug=None):
    """Fetches the AI Interview ID for a candidate, checking job-specific fields first."""
    log.info("recruitcrm.fetch_candidate_interview_id.called", candidate_slug=candidate_slug, job_slug=job_slug)
    if job_slug:
        job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug)
        if job_specific_fields:
            for field_data in job_specific_fields.values():
                if isinstance(field_data, dict) and field_data.get('label') == 'AI Interview ID':
                    interview_id = field_data.get('value')
                    if interview_id:
                        log.info("recruitcrm.fetch_candidate_interview_id.found_in_job_specific_fields", candidate_slug=candidate_slug, job_slug=job_slug)
                        return interview_id

    candidate_data = fetch_recruitcrm_candidate(candidate_slug)
    if candidate_data:
        custom_fields = candidate_data.get('data', {}).get('custom_fields', [])
        for field in custom_fields:
            if isinstance(field, dict) and field.get('field_name') == 'AI Interview ID':
                interview_id = field.get('value')
                if interview_id:
                    log.info("recruitcrm.fetch_candidate_interview_id.found_in_general_fields", candidate_slug=candidate_slug)
                    return interview_id
    log.warning("recruitcrm.fetch_candidate_interview_id.not_found", candidate_slug=candidate_slug, job_slug=job_slug)
    return None

def fetch_recruitcrm_job(slug, include_custom_fields=True):
    """Fetches job data from RecruitCRM using the job's slug."""
    log.info("recruitcrm.fetch_recruitcrm_job.called", slug=slug, include_custom_fields=include_custom_fields)
    url = f'https://api.recruitcrm.io/v1/jobs/{slug}'
    params = {'include': 'custom_fields'} if include_custom_fields else None
    try:
        response = requests.get(url, headers=get_recruitcrm_headers(), params=params)
        response.raise_for_status()
        log.info("recruitcrm.fetch_recruitcrm_job.success", slug=slug)
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_job.failed", slug=slug, error=str(e))
        return None

def fetch_hiring_pipeline():
    """Fetches the entire hiring pipeline (all possible stages)."""
    log.info("recruitcrm.fetch_hiring_pipeline.called")
    url = "https://api.recruitcrm.io/v1/hiring-pipeline"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        log.info("recruitcrm.fetch_hiring_pipeline.success")
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_hiring_pipeline.failed", error=str(e))
        return []

def push_to_recruitcrm_internal(candidate_slug, html_summary):
    """Internal function to push summary, returns success status."""
    log.info("recruitcrm.push_to_recruitcrm_internal.called", candidate_slug=candidate_slug)
    try:
        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {'candidate_summary': (None, html_summary)}
        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        log.info("recruitcrm.push_to_recruitcrm_internal.response", candidate_slug=candidate_slug, status_code=response.status_code)
        return response.status_code == 200
    except Exception as e:
        log.error("recruitcrm.push_summary.exception", slug=candidate_slug, error=str(e))
        return False

def fetch_recruitcrm_assigned_candidates(job_slug, status_id=None):
    """Fetches assigned candidates for a job from RecruitCRM."""
    log.info("recruitcrm.fetch_recruitcrm_assigned_candidates.called", job_slug=job_slug, status_id=status_id)
    url = f"https://api.recruitcrm.io/v1/jobs/{job_slug}/assigned-candidates"
    params = {'status_id': status_id} if status_id else {}
    try:
        response = requests.get(url, headers=get_recruitcrm_headers(), params=params)
        response.raise_for_status()
        data = response.json().get('data', [])
        log.info("recruitcrm.fetch_recruitcrm_assigned_candidates.success", job_slug=job_slug, status_id=status_id, count=len(data))
        return data
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_assigned_candidates.failed", job_slug=job_slug, error=str(e))
        return []

def fetch_alpharun_interview(job_opening_id, interview_id):
    """Fetches interview data from AlphaRun."""
    log.info("recruitcrm.fetch_alpharun_interview.called", job_opening_id=job_opening_id, interview_id=interview_id)
    url = f"https://api.alpharun.com/api/v1/job-openings/{job_opening_id}/interviews/{interview_id}"
    try:
        response = requests.get(url, headers=get_alpharun_headers())
        response.raise_for_status()
        log.info("recruitcrm.fetch_alpharun_interview.success", job_opening_id=job_opening_id, interview_id=interview_id)
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("alpharun.fetch_interview.failed", interview_id=interview_id, error=str(e))
        return None

def fetch_candidate_notes(candidate_slug):
    """Fetches all notes for a candidate from RecruitCRM."""
    log.info("recruitcrm.fetch_candidate_notes.called", candidate_slug=candidate_slug)
    url = 'https://api.recruitcrm.io/v1/notes/search'
    params = {
        'related_to': candidate_slug,
        'related_to_type': 'candidate'

    }
    try:
        response = requests.get(url, headers=get_recruitcrm_headers(), params=params)
        response.raise_for_status()
        data = response.json()
        
        # RecruitCRM sometimes returns list directly, sometimes {'data': [...]}
        if isinstance(data, list):
            notes = data
        else:
            notes = data.get('data', [])
            
        log.info("recruitcrm.fetch_candidate_notes.success", 
                 candidate_slug=candidate_slug, 
                 note_count=len(notes))
        return notes
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_candidate_notes.failed", 
                 candidate_slug=candidate_slug, 
                 error=str(e))
        return []

# --- NEW MINIMALIST FIX ---
# Based on your successful Postman test
def create_recruitcrm_note(candidate_slug, job_slug, note_content):
    """
    Creates a new note associated with a candidate using the minimal required payload.
    """
    log.info("recruitcrm.create_recruitcrm_note.called",
             candidate_slug=candidate_slug, job_slug=job_slug)

    url = "https://api.recruitcrm.io/v1/notes"

    # --- UPDATED MINIMAL PAYLOAD ---
    # Using only the fields from your test
    payload = {
        "description": note_content,       # <-- This will be the plain text from orchestrator.py
        "related_to": candidate_slug,
        "related_to_type": "candidate",
        "associated_jobs": [job_slug]
        # We are intentionally omitting associated_jobs, note_type_id, etc.,
        # as they are not in your minimal test and may be causing the 422 error.
    }
    # --- END OF UPDATED PAYLOAD ---

    try:
        response = requests.post(url, headers=get_recruitcrm_headers(), json=payload)
        response.raise_for_status()
        log.info("recruitcrm.create_recruitcrm_note.success",
                 candidate_slug=candidate_slug)
        return response.json()
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 422:
            log.error("recruitcrm.create_recruitcrm_note.failed_422",
                      error=str(e), payload_sent=payload)
        else:
            log.error("recruitcrm.create_recruitcrm_note.failed",
                      error=str(e))
        return None

    # --- ADD THIS NEW FUNCTION ---
def set_candidate_stage_by_slug(candidate_slug, job_slug, new_status_id):
    """Sets a candidate's stage for a specific job using slugs."""
    log.info("recruitcrm.set_candidate_stage.called",
             candidate_slug=candidate_slug, job_slug=job_slug, new_status_id=new_status_id)

    # This URL is from your Postman test
    url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}/hiring-stages/{job_slug}"

    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    remark_text = f"Candidate summary tool automation at {now_utc}"

    # This payload is based on your test. We'll set 'updated_by' to 0 for 'system'.
    payload = {
        "status_id": new_status_id,
        "remark": remark_text
    }

    try:
        response = requests.post(url, headers=get_recruitcrm_headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        log.info("recruitcrm.set_candidate_stage.success",
                 candidate_slug=candidate_slug, job_slug=job_slug, new_stage=data.get('status', {}).get('label'))
        return data
    except requests.exceptions.RequestException as e:
        log.error(
            "recruitcrm.set_candidate_stage.failed",
            candidate_slug=candidate_slug,
            job_slug=job_slug,
            error=str(e)
        )
        return None
