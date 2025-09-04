# helpers/recruitcrm_helpers.py
import os
import requests
import structlog

log = structlog.get_logger()

RECRUITCRM_API_KEY = os.getenv('RECRUITCRM_API_KEY')
ALPHARUN_API_KEY = os.getenv('ALPHARUN_API_KEY')

def get_recruitcrm_headers():
    """Returns the authorization headers for the RecruitCRM API."""
    if not RECRUITCRM_API_KEY:
        raise ValueError("RECRUITCRM_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {RECRUITCRM_API_KEY}',
        'Accept': 'application/json'
    }

def get_alpharun_headers():
    """Returns the authorization headers for the AlphaRun API."""
    if not ALPHARUN_API_KEY:
        raise ValueError("ALPHARUN_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {ALPHARUN_API_KEY}',
        'Content-Type': 'application/json'
    }

def fetch_recruitcrm_candidate(slug):
    """Fetches candidate data from RecruitCRM using the candidate's slug."""
    url = f'https://api.recruitcrm.io/v1/candidates/{slug}'
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_candidate.failed", slug=slug, error=str(e))
        return None

def fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug):
    """Fetches job-specific custom fields for a candidate from RecruitCRM."""
    url = f"https://api.recruitcrm.io/v1/candidates/associated-field/{candidate_slug}/{job_slug}"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        if response.status_code == 200:
            return response.json().get('data', {})
        else:
            log.error(
                "recruitcrm.fetch_job_specific_fields.failed",
                status=response.status_code
            )
            return None
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_job_specific_fields.exception", error=str(e))
        return None

def fetch_candidate_interview_id(candidate_slug, job_slug=None):
    """Fetches the AI Interview ID for a candidate, checking job-specific fields first."""
    if job_slug:
        job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug)
        if job_specific_fields:
            for field_data in job_specific_fields.values():
                if isinstance(field_data, dict) and field_data.get('label') == 'AI Interview ID':
                    interview_id = field_data.get('value')
                    if interview_id:
                        return interview_id

    candidate_data = fetch_recruitcrm_candidate(candidate_slug)
    if candidate_data:
        custom_fields = candidate_data.get('data', {}).get('custom_fields', [])
        for field in custom_fields:
            if isinstance(field, dict) and field.get('field_name') == 'AI Interview ID':
                interview_id = field.get('value')
                if interview_id:
                    return interview_id
    return None

def fetch_recruitcrm_job(slug, include_custom_fields=True):
    """Fetches job data from RecruitCRM using the job's slug."""
    url = f'https://api.recruitcrm.io/v1/jobs/{slug}'
    params = {'include': 'custom_fields'} if include_custom_fields else None
    try:
        response = requests.get(url, headers=get_recruitcrm_headers(), params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_job.failed", slug=slug, error=str(e))
        return None

def fetch_hiring_pipeline():
    """Fetches the entire hiring pipeline (all possible stages)."""
    url = "https://api.recruitcrm.io/v1/hiring-pipeline"
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_hiring_pipeline.failed", error=str(e))
        return []

def push_to_recruitcrm_internal(candidate_slug, html_summary):
    """Internal function to push summary, returns success status."""
    try:
        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {'candidate_summary': (None, html_summary)}
        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        return response.status_code == 200
    except Exception as e:
        log.error("recruitcrm.push_summary.exception", slug=candidate_slug, error=str(e))
        return False

def fetch_recruitcrm_assigned_candidates(job_slug, status_id=None):
    """Fetches assigned candidates for a job from RecruitCRM."""
    url = f"https://api.recruitcrm.io/v1/jobs/{job_slug}/assigned-candidates"
    params = {'status_id': status_id} if status_id else {}
    try:
        response = requests.get(url, headers=get_recruitcrm_headers(), params=params)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        log.error("recruitcrm.fetch_assigned_candidates.failed", job_slug=job_slug, error=str(e))
        return []

def fetch_alpharun_interview(job_opening_id, interview_id):
    """Fetches interview data from AlphaRun."""
    url = f"https://api.alpharun.com/api/v1/job-openings/{job_opening_id}/interviews/{interview_id}"
    try:
        response = requests.get(url, headers=get_alpharun_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error("alpharun.fetch_interview.failed", interview_id=interview_id, error=str(e))
        return None