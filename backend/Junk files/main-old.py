# main.py - Summary Worker Function
# Processes Cloud Tasks and orchestrates candidate summary generation

import logging
import sys
import json
import os
import time
from datetime import datetime
import requests
from flask import jsonify, request
from google.cloud import firestore

# --- NEW: Import the Google Cloud Logging library ---
try:
    import google.cloud.logging
except ImportError:
    google = None
    logging.warning("google.cloud.logging not found. Please add 'google-cloud-logging' to requirements.txt")


# --- GCP Compliant Structured Logging Setup ---
try:
    # Check if the import was successful
    if 'google.cloud' in sys.modules and hasattr(google, 'cloud') and hasattr(google.cloud, 'logging'):
        client = google.cloud.logging.Client()
        handler = client.get_default_handler()
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Remove existing handlers
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info("Structured logging initialized successfully.")
    else:
        raise Exception("google.cloud.logging module not available.")
except Exception as e:
    # Fallback to basic logging if GCP logging fails
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize GCP structured logging: {e}. Falling back to basicConfig.")
# --- End of Logging Setup ---


# Environment variables
# --- FIX 1: Updated to the correct, verified Cloud Run URL ---
FLASK_APP_URL = os.environ.get('FLASK_APP_URL', 'https://candidate-summary-api-hdg54dp7ga-uc.a.run.app')
WORKER_VERSION = '1.0.0'

# Initialize Firestore
db = firestore.Client()

# Configuration
REQUEST_TIMEOUT = 60  # seconds

# --- NEW: Fallback config if Firestore read fails ---
# Based on your webhook_config JSON
FALLBACK_CONFIG = {
    'use_quil': True,
    'include_fireflies': False,
    'proceed_without_interview': False,
    'additional_context': '',
    'prompt_type': 'summary-for-platform-v2',  # Fallback prompt,  # Fallback prompt
    # --- ADDED new config keys ---
    'auto_push': False,
    'create_tracking_note': False,
    'auto_push_delay_seconds': 0
}


# --- NEW: Function to fetch dynamic config from Firestore ---
def get_dynamic_config():
    """Fetch dynamic configuration from Firestore."""
    try:
        doc_ref = db.collection('webhook_config').document('default')
        doc = doc_ref.get()
        if doc.exists:
            config_data = doc.to_dict()
            logger.info("Fetched dynamic config from Firestore.")
            # Map Firestore fields to the format generate_summary expects
            # This provides a safe mapping layer.
            return {
                'use_quil': config_data.get('use_quil', FALLBACK_CONFIG['use_quil']),
                'include_fireflies': config_data.get('use_fireflies', FALLBACK_CONFIG['include_fireflies']),
                'proceed_without_interview': config_data.get('proceed_without_interview', FALLBACK_CONFIG['proceed_without_interview']),
                'additional_context': config_data.get('additional_context', FALLBACK_CONFIG['additional_context']),
                'prompt_type': config_data.get('default_prompt_id', FALLBACK_CONFIG['prompt_type']),
                # --- ADDED mapping for new keys ---
                'auto_push': config_data.get('auto_push', FALLBACK_CONFIG['auto_push']),
                'create_tracking_note': config_data.get('create_tracking_note', FALLBACK_CONFIG['create_tracking_note']),
                'auto_push_delay_seconds': config_data.get('auto_push_delay_seconds', FALLBACK_CONFIG['auto_push_delay_seconds'])
            }
        else:
            logger.warning(
                "Firestore config doc 'webhook_config/default' not found. Using fallback.",
                extra={"json_fields": {"config_source": "fallback"}}
            )
            return FALLBACK_CONFIG
    except Exception as e:
        logger.error(
            f"Failed to fetch Firestore config: {e}. Using fallback.",
            extra={"json_fields": {"error": str(e), "config_source": "fallback"}}
        )
        return FALLBACK_CONFIG


def log_to_firestore(run_data):
    """Log the summary generation run to Firestore."""
    try:
        # Use a structured ID for easier querying
        # Format: YYYYMMDD_HHMMSS_CandidateSlug_JobSlug
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate_slug = run_data.get('candidate_slug', 'unknown')
        job_slug = run_data.get('job_slug', 'unknown')
        doc_id = f"{timestamp_str}_{candidate_slug}_{job_slug}"

        doc_ref = db.collection('candidate_summary_runs').document(doc_id)
        run_data['timestamp'] = firestore.SERVER_TIMESTAMP
        doc_ref.set(run_data)
        logger.info(
            "Logged run to Firestore",
            extra={"json_fields": {"firestore_id": doc_ref.id, "candidate_slug": candidate_slug, "job_slug": job_slug}}
        )
        return doc_ref.id
    except Exception as e:
        logger.error(
            f"Failed to log to Firestore: {e}",
            extra={"json_fields": {"error": str(e), "candidate_slug": run_data.get('candidate_slug')}}
        )
        return None

# --- FIX 2: Updated function to support POST method ---
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

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT * 2)  # Double timeout for generation
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
    # --- End of restored code block ---

# --- ADDED: Stub function for creating a note ---
def handle_note_creation(candidate_slug, job_slug, summary_html, triggered_by):
    """(Stub) Creates a tracking note in RecruitCRM."""
    log_context = {"action": "create_note", "candidate_slug": candidate_slug, "job_slug": job_slug}
    try:
        logger.info("Creating tracking note (stub)", extra={"json_fields": log_context})
        # TODO: Implement API call to RecruitCRM to create a note
        # Example:
        # note_payload = {
        #     'candidate_slug': candidate_slug,
        #     'job_slug': job_slug,
        #     'note_html': summary_html,
        #     'triggered_by_email': triggered_by.get('email') if triggered_by else None
        # }
        # response = requests.post(f"{FLASK_APP_URL}/api/create-note", json=note_payload, timeout=REQUEST_TIMEOUT)
        # response.raise_for_status()
        # logger.info("✅ Tracking note created successfully.")

        # Simulating success for now
        time.sleep(0.1) # Simulate network delay
        logger.info("Tracking note created (stub)", extra={"json_fields": {**log_context, "success": True}})
        return {'success': True, 'error': None, 'message': 'Note created (stub)'}

    except Exception as e:
        error_msg = f"Failed to create tracking note: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to create note'}

# --- ADDED: Stub function for auto-pushing candidate ---
def handle_auto_push(candidate_slug, job_slug, delay_seconds, triggered_by):
    """(Stub) Pushes candidate to the next stage."""
    log_context = {
        "action": "auto_push",
        "candidate_slug": candidate_slug,
        "job_slug": job_slug,
        "delay_seconds": delay_seconds
    }
    try:
        logger.info(f"Auto-pushing candidate (stub) with {delay_seconds}s delay...", extra={"json_fields": log_context})
        # TODO: Implement API call to RecruitCRM to push stage
        # Example:
        # push_payload = {
        #     'candidate_slug': candidate_slug,
        #     'job_slug': job_slug,
        #     'delay_seconds': delay_seconds,
        #     'triggered_by_email': triggered_by.get('email') if triggered_by else None
        # }
        # response = requests.post(f"{FLASK_APP_URL}/api/push-stage", json=push_payload, timeout=REQUEST_TIMEOUT)
        # response.raise_for_status()
        # logger.info("✅ Candidate auto-push queued successfully.")

        # Simulating success for now
        time.sleep(0.1) # Simulate network delay
        logger.info("Candidate auto-push triggered (stub)", extra={"json_fields": {**log_context, "success": True}})
        return {'success': True, 'error': None, 'message': 'Auto-push triggered (stub)'}

    except Exception as e:
        error_msg = f"Failed to trigger auto-push: {e}"
        logger.error(error_msg, extra={"json_fields": {**log_context, "error": str(e), "success": False}})
        return {'success': False, 'error': str(e), 'message': 'Failed to trigger auto-push'}


def process_summary_task(candidate_slug, job_slug, task_metadata, updated_by=None):
    """
    Process a candidate summary task by testing endpoints and generating summary.
    Mirrors the UI flow from CandidateSummaryGenerator.jsx
    """

    # Base context for all logs in this task
    base_log_context = {
        "candidate_slug": candidate_slug,
        "job_slug": job_slug,
        **task_metadata
    }

    # --- NEW: Fetch dynamic config at the start of the process ---
    dynamic_config = get_dynamic_config()

    logger.info(
        "Starting summary generation",
        extra={"json_fields": {**base_log_context, "triggered_by": updated_by}}
    )
    logger.info(
        "Using config",
        extra={"json_fields": {**base_log_context, "prompt_id": dynamic_config.get('prompt_type')}}
    )

    # Initialize run data for Firestore logging
    run_data = {
        'candidate_slug': candidate_slug,
        'job_slug': job_slug,
        'tests': {},
        'sources_used': {
            'resume': False,
            'anna_ai': False,
            'quil': False,
            'fireflies': False
        },
        'generation': {},
        'worker_metadata': {
            'worker_version': WORKER_VERSION,
            'triggered_by': updated_by,  # Track who triggered this in RecruitCRM
            **task_metadata
        },
        'config_used': dynamic_config, # Log the config that was used for this run
        # --- ADDED: Placeholders for post-generation actions ---
        'post_actions': {
            'note_creation': None,
            'auto_push': None
        },
        'prompt_sources': {}
    }

    # --- Add top-level fields for easier querying in Firestore ---
    # These are duplicated but make filtering in Firestore much easier
    if updated_by:
        run_data['triggered_by_email'] = updated_by.get('email')

    run_data['success'] = False # Default to false, set to true on success
    # --- NEW: Add prompt_id as a top-level field for UI filtering ---
    run_data['prompt_id'] = dynamic_config.get('prompt_type')

    # --- FIX 2: Added method='POST' to all test_endpoint calls ---

    # Step 1: Test Candidate Data (BLOCKING)
    candidate_test = test_endpoint('/api/test-candidate', candidate_slug, job_slug, 'Candidate Data', method='POST')
    run_data['tests']['candidate_data'] = {
        'success': candidate_test['success'],
        'error': candidate_test['error']
    }

    # --- Add candidate/job names to top-level for Firestore ---
    if candidate_test['success'] and candidate_test['data']:
        # Frontend expects: apiStatus.candidate.data.candidate_name
        run_data['candidate_name'] = candidate_test['data'].get('candidate_name', 'N/A')

    if not candidate_test['success']:
        error_msg = 'BLOCKING: Candidate data not found. Stopping.'
        logger.error(error_msg, extra={"json_fields": {**base_log_context, "reason": "candidate_data_not_found"}})
        run_data['generation'] = {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': 'Candidate data not found (blocking)'
        }
        log_to_firestore(run_data)
        return False, "Candidate data not found", run_data

    # Step 2: Test Job Data (BLOCKING)
    job_test = test_endpoint('/api/test-job', candidate_slug, job_slug, 'Job Data', method='POST')
    run_data['tests']['job_data'] = {
        'success': job_test['success'],
        'error': job_test['error']
    }

    # --- Add job name to top-level for Firestore ---
    if job_test['success'] and job_test['data']:
        # Frontend expects: apiStatus.job.data.job_name
        run_data['job_name'] = job_test['data'].get('job_name', 'N/A')

    if not job_test['success']:
        error_msg = 'BLOCKING: Job data not found. Stopping.'
        logger.error(error_msg, extra={"json_fields": {**base_log_context, "reason": "job_data_not_found"}})
        run_data['generation'] = {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': 'Job data not found (blocking)'
        }
        log_to_firestore(run_data)
        return False, "Job data not found", run_data

    # Step 3: Test CV Data (OPTIONAL)
    cv_test = test_endpoint('/api/test-resume', candidate_slug, job_slug, 'CV Data', method='POST')
    run_data['tests']['cv_data'] = {
        'success': cv_test['success'],
        'error': cv_test['error']
    }
    if cv_test['success']:
        run_data['sources_used']['resume'] = True

    # Step 4: Test AI Interview (OPTIONAL)
    ai_test = test_endpoint('/api/test-interview', candidate_slug, job_slug, 'AI Interview', method='POST')
    run_data['tests']['ai_interview'] = {
        'success': ai_test['success'],
        'error': ai_test['error']
    }
    if ai_test['success']:
        run_data['sources_used']['anna_ai'] = True

    # Step 5: Test Quil Interview (OPTIONAL)
    quil_test = test_endpoint('/api/test-quil', candidate_slug, job_slug, 'Quil Interview', method='POST')
    run_data['tests']['quil_interview'] = {
        'success': quil_test['success'],
        'error': quil_test['error']
    }

    # Extract Quil note ID if available
    if quil_test['success'] and quil_test['data']:
        note_id = quil_test['data'].get('note_id')
        if note_id:
            run_data['tests']['quil_interview']['note_id'] = note_id
            run_data['sources_used']['quil'] = True

    # Log what sources we have before generation
    sources = [k for k, v in run_data['sources_used'].items() if v]
    logger.info(
        "Source availability check complete",
        extra={"json_fields": {**base_log_context, "sources": sources}}
    )

    # --- ADDED: Logic to check if we should proceed without interviews ---
    has_interview = run_data['sources_used']['anna_ai'] or run_data['sources_used']['quil']
    proceed_without_interview = dynamic_config.get('proceed_without_interview', False)

    if not has_interview and not proceed_without_interview:
        error_msg = "BLOCKING: No interview data (Anna/Quil) found and 'proceed_without_interview' is false. Stopping."
        logger.error(error_msg, extra={"json_fields": {**base_log_context, "reason": "no_interview_data"}})
        run_data['generation'] = {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': 'No interview data found and proceeding without it is disabled'
        }
        log_to_firestore(run_data)
        return False, "No interview data found", run_data
    elif not has_interview:
        logger.warning(
            "No interview data (Anna/Quil) found, but proceeding as 'proceed_without_interview' is true.",
            extra={"json_fields": {**base_log_context, "warning": "proceeding_without_interview"}}
        )
    # --- End of new logic ---


    # Step 6: Generate Summary
    # --- UPDATED: Pass the dynamic_config to the generation function ---
    generation_result = generate_summary(candidate_slug, job_slug, dynamic_config)
    run_data['generation'] = generation_result
    run_data['success'] = generation_result['success'] # Update top-level success

    # Capture the sources confirmed by the generation endpoint
    prompt_sources = {}
    if generation_result.get('data'):
        raw_sources = generation_result['data'].get('sources_used') or {}
        if isinstance(raw_sources, dict):
            prompt_sources = {k: bool(v) for k, v in raw_sources.items()}
            run_data['prompt_sources'] = prompt_sources

            # Merge prompt confirmed sources into top-level sources_used tracker
            for source_key, was_used in prompt_sources.items():
                if was_used and source_key in run_data['sources_used']:
                    run_data['sources_used'][source_key] = True

    if prompt_sources:
        logger.info(
            "Prompt sources confirmed",
            extra={"json_fields": {**base_log_context, "prompt_sources": prompt_sources}}
        )
    elif generation_result['success']:
        logger.warning(
            "Prompt sources not reported",
            extra={"json_fields": {**base_log_context, "prompt_sources_present": False}}
        )

    # --- Add summary html to top level for display in Firestore ---
    # --- FIX: Changed 'generation_config' to 'generation_result' ---
    if generation_result['success'] and generation_result['data']:
        run_data['summary_html'] = generation_result['data'].get('summary', '')

    # --- UPDATED: This section now runs AFTER generation but BEFORE logging ---
    if generation_result['success']:
        logger.info(
            "Summary generation complete. Checking post-actions...",
            extra={"json_fields": base_log_context}
        )

        # Check if note creation is enabled
        if dynamic_config.get('create_tracking_note'):
            note_result = handle_note_creation(
                candidate_slug,
                job_slug,
                run_data.get('summary_html', ''),
                updated_by
            )
            run_data['post_actions']['note_creation'] = note_result
        else:
            logger.info("Skipping note creation (disabled in config).", extra={"json_fields": base_log_context})

        # Check if auto-push is enabled
        if dynamic_config.get('auto_push'):
            push_result = handle_auto_push(
                candidate_slug,
                job_slug,
                dynamic_config.get('auto_push_delay_seconds', 0),
                updated_by
            )
            run_data['post_actions']['auto_push'] = push_result
        else:
            logger.info("Skipping auto-push (disabled in config).", extra={"json_fields": base_log_context})

    else:
        logger.error(
            f"Summary generation failed: {generation_result['error']}",
            extra={"json_fields": {**base_log_context, "error": generation_result['error']}}
        )

    # Log to Firestore (now includes post_action results)
    firestore_id = log_to_firestore(run_data)
    run_data['firestore_id'] = firestore_id # Add ID to return data

    if generation_result['success']:
        logger.info(
            f"Process complete. Firestore ID: {firestore_id}",
            extra={"json_fields": {**base_log_context, "success": True, "firestore_id": firestore_id}}
        )
        return True, "Summary generated successfully", run_data
    else:
        logger.error(
            f"Process failed. Firestore ID: {firestore_id}",
            extra={"json_fields": {**base_log_context, "success": False, "firestore_id": firestore_id}}
        )
        return False, generation_result['error'], run_data


def summary_worker(request):
    """
    Cloud Function entry point.
    Triggered by Cloud Tasks queue.
    """

    logger.info("Summary Worker Invoked")
    payload = {} # Initialize payload for error logging

    # Validate method
    if request.method != 'POST':
        logger.warning("Method Not Allowed", extra={"json_fields": {"method": request.method}})
        return jsonify({"error": "Method Not Allowed"}), 405

    try:
        # Parse task payload
        payload = request.get_json(silent=True)

        if not payload:
            logger.error("No JSON payload received", extra={"json_fields": {"error": "Invalid payload"}})
            return jsonify({"error": "Invalid payload"}), 400

        # Extract required fields
        candidate_slug = payload.get('candidate_slug')
        job_slug = payload.get('job_slug')

        # Extract optional updated_by from webhook payload
        webhook_payload = payload.get('webhook_payload', {})
        updated_by = webhook_payload.get('updated_by')

        if not candidate_slug or not job_slug:
            logger.error(
                "Missing required fields",
                extra={"json_fields": {"error": "Missing required fields", "payload": payload}}
            )
            return jsonify({
                "error": "Missing required fields",
                "required": ["candidate_slug", "job_slug"]
            }), 400

        # Extract task metadata
        task_metadata = {
            'cloud_task_id': request.headers.get('X-CloudTasks-TaskName', 'unknown'),
            'retry_attempt': int(request.headers.get('X-CloudTasks-TaskRetryCount', 0))
        }

        # This is now the primary log message for a task
        logger.info("Processing summary task", extra={
            "json_fields": {
                "candidate_slug": candidate_slug,
                "job_slug": job_slug,
                "cloud_task_id": task_metadata.get('cloud_task_id'),
                "retry_attempt": task_metadata.get('retry_attempt'),
                "triggered_by": updated_by
            }
        })

        # Process the task
        success, message, run_data = process_summary_task(
            candidate_slug,
            job_slug,
            task_metadata,
            updated_by
        )

        # --- FIX 3: Removed duplicated/indented lines that caused IndentationError ---

        if success:
            return jsonify({
                "status": "success",
                "message": message,
                "candidate_slug": candidate_slug,
                "job_slug": job_slug,
                "sources_used": run_data['sources_used'],
                "summary_length": run_data['generation']['summary_length']
            }), 200
        else:
            # Return 500 for retriable errors, 400 for permanent failures
            status_code = 400 if "not found" in message.lower() else 500
            return jsonify({
                "status": "error",
                "message": message,
                "candidate_slug": candidate_slug,
                "job_slug": job_slug
            }), status_code

    except Exception as e:
        logger.error(
            f"Worker error: {str(e)}",
            extra={"json_fields": {
                "error": str(e),
                "candidate_slug": payload.get('candidate_slug'),
                "job_slug": payload.get('job_slug')
            }}
        )
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

# --- FIX: Removed the extra '}' that was causing a SyntaxError ---
