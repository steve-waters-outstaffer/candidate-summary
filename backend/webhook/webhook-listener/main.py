# main.py - Webhook Listener with Cloud Tasks Integration
import logging
import sys
import json
import os
from flask import jsonify, request
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import datetime

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
        logger.info("Structured logging initialized successfully for Webhook Listener.")
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
GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID')
CLOUD_TASKS_QUEUE = os.environ.get('CLOUD_TASKS_QUEUE', 'candidate-summary-queue')
CLOUD_TASKS_LOCATION = os.environ.get('CLOUD_TASKS_LOCATION', 'us-central1')
WORKER_FUNCTION_URL = os.environ.get('WORKER_FUNCTION_URL')

# --- Target Status ID for Filtering ---
# This is the ID for "2.0.1. AI Summary - For Generation"
TARGET_STATUS_ID = 726194
# ---

# Initialize Cloud Tasks client
tasks_client = tasks_v2.CloudTasksClient()


def create_summary_task(candidate_slug, job_slug, payload):
    """Create a Cloud Task to process the candidate summary."""
    try:
        # Construct the fully qualified queue name
        parent = tasks_client.queue_path(GCP_PROJECT_ID, CLOUD_TASKS_LOCATION, CLOUD_TASKS_QUEUE)

        # Construct the task payload
        task_payload = {
            'candidate_slug': candidate_slug,
            'job_slug': job_slug,
            'webhook_payload': payload  # Pass full payload for reference
        }

        # Create the task
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': WORKER_FUNCTION_URL,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(task_payload).encode()
            }
        }

        # Optional: Schedule task with delay (useful for rate limiting)
        # schedule_time = timestamp_pb2.Timestamp()
        # schedule_time.FromDatetime(datetime.datetime.utcnow() + datetime.timedelta(seconds=10))
        # task['schedule_time'] = schedule_time

        # Create the task
        response = tasks_client.create_task(request={'parent': parent, 'task': task})

        # --- CONVERTED TO STRUCTURED LOGGING ---
        logger.info("Cloud task created", extra={
            "json_fields": {
                "event": "cloud_task_created",
                "task_name": response.name,
                "candidate_slug": candidate_slug,
                "job_slug": job_slug
            }
        })
        return True, response.name

    except Exception as e:
        # --- CONVERTED TO STRUCTURED LOGGING ---
        logger.error("Cloud task creation failed", extra={
            "json_fields": {
                "event": "cloud_task_creation_failed",
                "error": str(e),
                "candidate_slug": candidate_slug,
                "job_slug": job_slug
            }
        })
        return False, str(e)


def webhook_listener(request):
    """Receives webhook payload, filters by status, and creates Cloud Task."""

    logger.info("Incoming Webhook Request")

    # 1. Check for correct method
    if request.method != 'POST':
        logger.warning("Method Not Allowed", extra={"json_fields": {"method": request.method}})
        return jsonify({"error": "Method Not Allowed"}), 405

    # 2. Validate environment variables
    missing_vars = [
        k for k, v in {
            'GCP_PROJECT_ID': GCP_PROJECT_ID,
            'WORKER_FUNCTION_URL': WORKER_FUNCTION_URL
        }.items() if not v
    ]
    if missing_vars:
        # --- ENRICHED LOGGING ---
        logger.error("Missing required environment variables", extra={
            "json_fields": {"missing": missing_vars}
        })
        return jsonify({
            "error": "Server configuration error",
            "missing": missing_vars
        }), 500

    # 3. Parse and validate payload
    try:
        payload = request.get_json(silent=True)

        if not payload:
            logger.warning("No JSON payload found")
            return jsonify({"error": "Invalid payload"}), 400

        # Log the full payload for debugging
        # --- CONVERTED TO STRUCTURED LOGGING ---
        logger.info("Webhook payload received", extra={"json_fields": {"webhook_payload": payload}})

        # --- FILTER LOGIC (APPLIED TO ROOT PAYLOAD) ---
        current_status = payload.get('status', {})
        current_status_id = current_status.get('status_id')
        current_status_label = current_status.get('label', 'N/A')

        # Log stage check with structured JSON
        # --- CONVERTED TO STRUCTURED LOGGING ---
        logger.info("Stage filter check", extra={
            "json_fields": {
                "event": "stage_filter_check",
                "current_stage_id": current_status_id,
                "current_stage_label": current_status_label,
                "target_stage_id": TARGET_STATUS_ID
            }
        })

        # Check if the status ID matches your target
        if current_status_id != TARGET_STATUS_ID:
            # --- CONVERTED TO STRUCTURED LOGGING ---
            logger.info("Stage filter result: skipped", extra={
                "json_fields": {
                    "event": "stage_filter_result",
                    "filter_matched": False,
                    "current_stage_id": current_status_id,
                    "target_stage_id": TARGET_STATUS_ID,
                    "action": "skipped"
                }
            })
            # Return 200 OK so RecruitCRM knows the webhook was
            # received successfully and doesn't try to send it again.
            return jsonify({
                "status": "skipped",
                "message": f"Candidate stage '{current_status_label}' is not the target stage."
            }), 200

        # --- CONVERTED TO STRUCTURED LOGGING ---
        logger.info("Stage filter result: proceeding", extra={
            "json_fields": {
                "event": "stage_filter_result",
                "filter_matched": True,
                "current_stage_id": current_status_id,
                "target_stage_id": TARGET_STATUS_ID,
                "action": "proceeding_to_queue"
            }
        })
        # --- FILTER LOGIC ENDS ---

        # Extract slugs now that filter has passed
        candidate_slug = payload.get('candidate_slug')
        job_slug = payload.get('job_slug')

        # Validate required fields
        if not candidate_slug or not job_slug:
            # --- CONVERTED TO STRUCTURED LOGGING ---
            logger.error("Webhook validation error: missing required fields", extra={
                "json_fields": {
                    "event": "validation_error",
                    "error": "missing_required_fields",
                    "candidate_slug_present": bool(candidate_slug),
                    "job_slug_present": bool(job_slug),
                    "payload_keys": list(payload.keys())
                }
            })
            return jsonify({
                "error": "Missing required fields after filter",
                "required": ["candidate_slug", "job_slug"],
                "received": {
                    "candidate_slug": bool(candidate_slug),
                    "job_slug": bool(job_slug)
                },
                "payload_keys": list(payload.keys())
            }), 400

        # Log task queue attempt
        # --- CONVERTED TO STRUCTURED LOGGING ---
        logger.info("Task queue attempt", extra={
            "json_fields": {
                "event": "task_queue_attempt",
                "candidate_slug": candidate_slug,
                "job_slug": job_slug
            }
        })

        # 4. Create Cloud Task (Pass the original full payload)
        success, result = create_summary_task(candidate_slug, job_slug, payload)

        if success:
            # --- CONVERTED TO STRUCTURED LOGGING ---
            logger.info("Task queue success", extra={
                "json_fields": {
                    "event": "task_queue_success",
                    "candidate_slug": candidate_slug,
                    "job_slug": job_slug,
                    "task_name": result
                }
            })
            return jsonify({
                "status": "queued",
                "message": "Summary generation task queued successfully",
                "task_name": result,
                "candidate_slug": candidate_slug,
                "job_slug": job_slug
            }), 200
        else:
            # --- CONVERTED TO STRUCTURED LOGGING ---
            logger.error("Task queue failure", extra={
                "json_fields": {
                    "event": "task_queue_failure",
                    "candidate_slug": candidate_slug,
                    "job_slug": job_slug,
                    "error": result
                }
            })
            return jsonify({
                "status": "error",
                "message": "Failed to queue task",
                "error": result
            }), 500

    except Exception as e:
        # --- ENRICHED LOGGING ---
        logger.error(f"Error processing webhook: {e}", extra={
            "json_fields": {
                "event": "webhook_processing_exception",
                "error": str(e)
            }
        })
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

