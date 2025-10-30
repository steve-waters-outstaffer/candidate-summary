# logging_helpers.py
# Sets up structured logging and provides logging utility functions.

import logging
import sys
import json
import os
from datetime import datetime
from google.cloud import firestore

# --- NEW: Import the Google Cloud Logging library ---
try:
    import google.cloud.logging
except ImportError:
    google = None
    logging.warning("google.cloud.logging not found. Please add 'google-cloud-logging' to requirements.txt")

# --- Import DB from config ---
# This is safe because config.py has no imports from this file.
try:
    from config import db
except ImportError:
    logging.error("CRITICAL: Could not import 'db' from config.py. Is the file missing?")
    # Fallback for db client if config fails, though logging will be impaired.
    db = firestore.Client()


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