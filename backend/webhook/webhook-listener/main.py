# main.py (Optimized for Google Cloud Functions/Cloud Run Logging)
import logging
import sys
import json
from flask import jsonify, request

# Configure logging once at the module level (before the handler function)
# All output to sys.stdout and sys.stderr is automatically captured by the GCF environment.
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def webhook_listener(request):
    """Receives and logs the webhook payload in a GCF-compatible way."""

    logger.info("--- Incoming Webhook Request ---")

    # 1. Check for the correct method
    if request.method != 'POST':
        return jsonify({"error": "Method Not Allowed"}), 405

    # 2. Log Request Headers
    logger.info("Headers:")
    headers_log = {}
    for header, value in request.headers.items():
        headers_log[header] = value

    # Log headers as structured JSON for easy inspection/filtering
    # Use standard print() for structured JSON output
    print(json.dumps({"headers": headers_log}))

    # 3. Log Request Body (Payload)
    try:
        payload = request.get_json(silent=True)

        if payload is not None:
            logger.info("Payload Received:")
            # Print the payload clearly, possibly causing a separate log entry
            print(json.dumps({"payload_data": payload}, indent=4))
        else:
            # Handle cases where the content-type is wrong or body is empty
            raw_data = request.get_data()
            logger.warning("No JSON payload found. Checking raw data.")
            print(f"Raw Data: {raw_data.decode('utf-8', errors='ignore')}")

    except Exception as e:
        logger.error(f"Error processing request body: {e}")

    # 4. Return a 200 OK Status
    return jsonify({"status": "received", "message": "Webhook successfully logged"}), 200