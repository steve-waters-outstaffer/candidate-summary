# main.py - Webhook Listener with Cloud Tasks Integration
import logging
import sys
import json
import os
from flask import jsonify, request
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import datetime

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

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

        logger.info(f"✅ Cloud Task created: {response.name}")
        return True, response.name

    except Exception as e:
        logger.error(f"❌ Failed to create Cloud Task: {e}")
        return False, str(e)


def webhook_listener(request):
    """Receives webhook payload, filters by status, and creates Cloud Task."""

    logger.info("--- Incoming Webhook Request ---")

    # 1. Check for correct method
    if request.method != 'POST':
        return jsonify({"error": "Method Not Allowed"}), 405

    # 2. Validate environment variables
    if not all([GCP_PROJECT_ID, WORKER_FUNCTION_URL]):
        logger.error("❌ Missing required environment variables")
        return jsonify({
            "error": "Server configuration error",
            "missing": [
                k for k, v in {
                    'GCP_PROJECT_ID': GCP_PROJECT_ID,
                    'WORKER_FUNCTION_URL': WORKER_FUNCTION_URL
                }.items() if not v
            ]
        }), 500

    # 3. Parse and validate payload
    try:
        payload = request.get_json(silent=True)

        if not payload:
            logger.warning("⚠️ No JSON payload found")
            return jsonify({"error": "Invalid payload"}), 400

        # Log the full payload for debugging
        logger.info("Payload received:")
        # Use a compact print for logs, but could be indent=2
        print(json.dumps({"webhook_payload": payload}))


        # --- NEW FILTER LOGIC (APPLIED TO ROOT PAYLOAD) ---
        current_status = payload.get('status', {})
        current_status_id = current_status.get('status_id')
        current_status_label = current_status.get('label', 'N/A')

        logger.info(f"ℹ️ Received webhook for candidate stage: {current_status_id} ({current_status_label})")

        # Check if the status ID matches your target
        if current_status_id != TARGET_STATUS_ID:
            logger.info(f"⏭️ SKIPPING task: Stage ID {current_status_id} does not match target {TARGET_STATUS_ID}.")
            # Return 200 OK so RecruitCRM knows the webhook was
            # received successfully and doesn't try to send it again.
            return jsonify({
                "status": "skipped",
                "message": f"Candidate stage '{current_status_label}' is not the target stage."
            }), 200

        logger.info(f"✅ STAGE MATCH: Proceeding to queue task for candidate.")
        # --- NEW FILTER LOGIC ENDS ---


        # Extract slugs now that filter has passed
        candidate_slug = payload.get('candidate_slug')
        job_slug = payload.get('job_slug')

        # Validate required fields
        if not candidate_slug or not job_slug:
            logger.error("❌ Missing required fields: candidate_slug or job_slug")
            logger.error(f"Payload structure: {list(payload.keys())}")
            return jsonify({
                "error": "Missing required fields after filter",
                "required": ["candidate_slug", "job_slug"],
                "received": {
                    "candidate_slug": bool(candidate_slug),
                    "job_slug": bool(job_slug)
                },
                "payload_keys": list(payload.keys())
            }), 400

        logger.info(f"📋 Processing: Candidate={candidate_slug}, Job={job_slug}")

        # 4. Create Cloud Task (Pass the original full payload)
        # --- ADDED LOGGING LINE ---
        logger.info(f"⏳ Attempting to enqueue task for candidate {candidate_slug}...")
        success, result = create_summary_task(candidate_slug, job_slug, payload)

        if success:
            return jsonify({
                "status": "queued",
                "message": "Summary generation task queued successfully",
                "task_name": result,
                "candidate_slug": candidate_slug,
                "job_slug": job_slug
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to queue task",
                "error": result
            }), 500

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500
