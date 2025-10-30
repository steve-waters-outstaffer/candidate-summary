# main.py - Summary Worker Function
# Cloud Function entry point. Processes Cloud Tasks.

from flask import jsonify, request

# --- Import dependencies ---
from logging_helpers import logger
from orchestrator import process_summary_task


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

        # Process the task by calling the orchestrator
        success, message, run_data = process_summary_task(
            candidate_slug,
            job_slug,
            task_metadata,
            updated_by
        )

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

# Note: The extra '}' from your original file has been removed.