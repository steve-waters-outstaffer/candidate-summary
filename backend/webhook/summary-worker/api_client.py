# api_client.py
# Handles all external API calls (e.g., to the Flask app, RecruitCRM).

import requests
import time

# --- Import dependencies ---
from config import FLASK_APP_URL, REQUEST_TIMEOUT
from logging_helpers import logger


def test_endpoint(endpoint_path, candidate_slug, job_slug, endpoint_name, method='GET'):
    """Test an API endpoint and return success status."""
    url = f"{FLASK_APP_URL}{endpoint_path}"

    log_context = {
        "endpoint_name": endpoint_name,
        "method": method,
        "url": url,
        "candidate_slug": candidate_slug,
        "job_slug": job_slug
    }

    # Data is sent as JSON for POST, params for GET
    payload = {
        'candidate_slug': candidate_slug,
        'job_slug': job_slug
    }

    try:
        logger.info(f"Testing {endpoint_name} ({method})...", extra={"json_fields": log_context})

        if method == 'POST':
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        else: # Default to GET
            response = requests.get(url, params=payload, timeout=REQUEST_TIMEOUT)

        response.raise_for_status()

        data = response.json()
        success = data.get('available', False) or data.get('success', False)

        logger.info(
            f"{endpoint_name}: {'Available' if success else 'Not available'}",
            extra={"json_fields": {**log_context, "success": success}}
        )

        return {
            'success': success,
            'error': None if success else data.get('message', 'Not available'),
            'data': data
        }

    except requests.exceptions.Timeout:
        error_msg = 'Request timeout'
        logger.error(
            f"{endpoint_name}: {error_msg}",
            extra={"json_fields": {**log_context, "error": error_msg}}
        )
        return {
            'success': False,
            'error': error_msg,
            'data': None
        }
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logger.error(
            f"{endpoint_name}: {error_msg}",
            extra={"json_fields": {**log_context, "error": error_msg}}
        )
        return {
            'success': False,
            'error': error_msg,
            'data': None
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(
            f"{endpoint_name}: {error_msg}",
            extra={"json_fields": {**log_context, "error": error_msg}}
        )
        return {
            'success': False,
            'error': str(e),
            'data': None
        }


def generate_summary(candidate_slug, job_slug, config):
    """Call the generate summary endpoint."""
    url = f"{FLASK_APP_URL}/api/generate-summary"

    log_context = {
        "candidate_slug": candidate_slug,
        "job_slug": job_slug,
        "prompt_type": config.get('prompt_type')
    }

    payload = {
        'candidate_slug': candidate_slug,
        'job_slug': job_slug,
        'alpharun_job_id': '',  # Required by API
        'interview_id': '',  # Required by API
        'fireflies_url': '',  # Required by API
        **config
    }

    try:
        logger.info(
            "Generating summary",
            extra={"json_fields": {**log_context, "config": config}}
        )
        start_time = time.time()

        # Double timeout for generation
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT * 2)
        response.raise_for_status()

        duration = time.time() - start_time
        data = response.json()
        success = data.get('success', False)
        summary = data.get('summary', '')

        logger.info(
            f"Summary generation: {'Complete' if success else 'Failed'}",
            extra={"json_fields": {**log_context, "success": success, "duration_seconds": round(duration, 2)}}
        )

        return {
            'success': success,
            'summary_length': len(summary) if summary else 0,
            'duration_seconds': duration,
            'error': None if success else data.get('error', 'Unknown error'),
            'data': data
        }

    except requests.exceptions.Timeout:
        duration = REQUEST_TIMEOUT * 2
        error_msg = 'Request timeout'
        logger.error(
            f"Summary generation: {error_msg}",
            extra={"json_fields": {**log_context, "error": error_msg, "duration_seconds": duration}}
        )
        return {
            'success': False,
            'summary_length': 0,
            'duration_seconds': duration,
            'error': error_msg,
            'data': None
        }
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logger.error(
            f"Summary generation failed: {error_msg}",
            extra={"json_fields": {**log_context, "error": error_msg}}
        )
        return {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': error_msg,
            'data': None
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(
            f"Summary generation: {error_msg}",
            extra={"json_fields": {**log_context, "error": error_msg}}
        )
        return {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': error_msg,
            'data': None
        }

# --- REFACTORED: Renamed from handle_note_creation ---
def handle_summary_push(candidate_slug, job_slug, summary_html, triggered_by):
    """Pushes the generated summary HTML to the candidate's main summary section in RecruitCRM."""
    log_context = {
        "action": "push_summary", # Updated action name
        "candidate_slug": candidate_slug,
        "job_slug": job_slug
    }

    # This endpoint is from your CandidateSummaryGenerator.jsx file
    url = f"{FLASK_APP_URL}/api/push-to-recruitcrm"

    payload = {
        'candidate_slug': candidate_slug,
        'html_summary': summary_html,
        'job_slug': job_slug,
        'triggered_by_email': triggered_by.get('email') if triggered_by else None
    }

    try:
        logger.info("Pushing summary to RecruitCRM...", extra={"json_fields": log_context})

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get('success'):
            logger.info("✅ Summary pushed to RecruitCRM successfully.", extra={"json_fields": {**log_context, "success": True}})
            return {'success': True, 'error': None, 'message': 'Summary pushed successfully'}
        else:
            error_msg = data.get('error', 'API returned success=false')
            logger.error(f"Failed to push summary to RecruitCRM: {error_msg}", extra={"json_fields": {**log_context, "error": error_msg, "success": False}})
            return {'success': False, 'error': error_msg, 'message': 'Failed to push summary'}

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to push summary: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to push summary'}
    except Exception as e:
        error_msg = f"Unexpected error in summary push: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to push summary'}


# --- NEW STUB for Action 2 ---
# --- UPDATED STUB for Action 2 ---
def handle_note_creation(candidate_slug, job_slug, note_html, triggered_by):
    """Creates a separate tracking note associated with the candidate and job."""
    log_context = {"action": "create_note", "candidate_slug": candidate_slug, "job_slug": job_slug}

    # We define a new endpoint that our Flask API must implement.
    # This endpoint will be responsible for finding the candidate_id and job_id from the slugs.
    url = f"{FLASK_APP_URL}/api/create-note"

    payload = {
        'candidate_slug': candidate_slug,
        'job_slug': job_slug,
        'note_html': note_html,
        'triggered_by_email': triggered_by.get('email') if triggered_by else None
    }

    try:
        logger.info("Creating tracking note...", extra={"json_fields": log_context})

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get('success'):
            logger.info("✅ Tracking note created successfully.", extra={"json_fields": {**log_context, "success": True}})
            return {'success': True, 'error': None, 'message': 'Note created successfully'}
        else:
            error_msg = data.get('error', 'API returned success=false')
            logger.error(f"Failed to create tracking note: {error_msg}", extra={"json_fields": {**log_context, "error": error_msg, "success": False}})
            return {'success': False, 'error': error_msg, 'message': 'Failed to create note'}

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create tracking note: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to create note'}
    except Exception as e:
        error_msg = f"Unexpected error in note creation: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to create note'}

    except Exception as e:
        error_msg = f"Failed to create tracking note: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to create note'}


# --- REPLACE THE STUB WITH THIS ---
# --- EDIT: Add target_stage_id to the function definition ---
def handle_stage_move(candidate_slug, job_slug, target_stage_id, delay_seconds, triggered_by):
    """Triggers the API to move the candidate to the next stage."""
    log_context = {
        "action": "move_stage",
        "candidate_slug": candidate_slug,
        "job_slug": job_slug,
        "delay_seconds": delay_seconds,
        "target_stage_id": target_stage_id  # --- EDIT: Add ID to logs ---
    }

    # This is the new endpoint we will create in single.py
    url = f"{FLASK_APP_URL}/api/move-stage"

    payload = {
        'candidate_slug': candidate_slug,
        'job_slug': job_slug,
        'target_stage_id': target_stage_id, # --- EDIT: Add ID to payload ---
        'triggered_by_email': triggered_by.get('email') if triggered_by else None
        # Note: We don't send the delay. The API will handle the logic.
    }

    try:
        logger.info(f"Triggering candidate stage move...", extra={"json_fields": log_context})

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get('success'):
            logger.info(f"✅ Candidate stage move triggered successfully: {data.get('message', '')}", extra={"json_fields": {**log_context, "success": True}})
            return {'success': True, 'error': None, 'message': data.get('message', 'Stage move triggered')}
        else:
            error_msg = data.get('error', 'API returned success=false')
            logger.error(f"Failed to trigger stage move: {error_msg}", extra={"json_fields": {**log_context, "error": error_msg, "success": False}})
            return {'success': False, 'error': error_msg, 'message': 'Failed to trigger stage move'}

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to trigger stage move: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to trigger stage move'}
    except Exception as e:
        error_msg = f"Unexpected error in stage move: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to trigger stage move'}
