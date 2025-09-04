# helpers/recruitcrm_helpers.py
import os
import requests
import structlog

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