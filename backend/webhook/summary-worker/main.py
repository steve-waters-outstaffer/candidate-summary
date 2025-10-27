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

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
FLASK_APP_URL = os.environ.get('FLASK_APP_URL', 'https://candidate-summary-api-us-central1-candidate-summary-ai.run.app')
WORKER_VERSION = '1.0.0'

# Initialize Firestore
db = firestore.Client()

# Configuration
REQUEST_TIMEOUT = 60  # seconds
DEFAULT_CONFIG = {
    'useQuil': True,
    'auto_push': False,  # We'll add push in Phase 3 with tracking note
    'includeFireflies': False,
    'additionalContext': ''
}


def log_to_firestore(run_data):
    """Log the summary generation run to Firestore."""
    try:
        doc_ref = db.collection('candidate_summary_runs').document()
        run_data['timestamp'] = firestore.SERVER_TIMESTAMP
        doc_ref.set(run_data)
        logger.info(f"✅ Logged run to Firestore: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"❌ Failed to log to Firestore: {e}")
        return None


def test_endpoint(endpoint_path, candidate_slug, job_slug, endpoint_name):
    """Test an API endpoint and return success status."""
    url = f"{FLASK_APP_URL}{endpoint_path}"
    params = {
        'candidate_slug': candidate_slug,
        'job_slug': job_slug
    }
    
    try:
        logger.info(f"🔍 Testing {endpoint_name}...")
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        success = data.get('available', False) or data.get('success', False)
        
        logger.info(f"{'✅' if success else '⚠️'} {endpoint_name}: {'Available' if success else 'Not available'}")
        
        return {
            'success': success,
            'error': None if success else data.get('message', 'Not available'),
            'data': data
        }
        
    except requests.exceptions.Timeout:
        logger.error(f"❌ {endpoint_name}: Request timeout")
        return {
            'success': False,
            'error': 'Request timeout',
            'data': None
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ {endpoint_name}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'data': None
        }
    except Exception as e:
        logger.error(f"❌ {endpoint_name}: Unexpected error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'data': None
        }


def generate_summary(candidate_slug, job_slug, config):
    """Call the generate summary endpoint."""
    url = f"{FLASK_APP_URL}/api/generate-summary"
    
    payload = {
        'candidate_slug': candidate_slug,
        'job_slug': job_slug,
        **config
    }
    
    try:
        logger.info(f"🤖 Generating summary with config: {config}")
        start_time = time.time()
        
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT * 2)  # Double timeout for generation
        response.raise_for_status()
        
        duration = time.time() - start_time
        data = response.json()
        
        success = data.get('success', False)
        summary = data.get('summary', '')
        
        logger.info(f"{'✅' if success else '❌'} Summary generation: {('Complete' if success else 'Failed')} ({duration:.2f}s)")
        
        return {
            'success': success,
            'summary_length': len(summary) if summary else 0,
            'duration_seconds': duration,
            'error': None if success else data.get('error', 'Unknown error'),
            'data': data
        }
        
    except requests.exceptions.Timeout:
        logger.error(f"❌ Summary generation: Request timeout")
        return {
            'success': False,
            'summary_length': 0,
            'duration_seconds': REQUEST_TIMEOUT * 2,
            'error': 'Request timeout',
            'data': None
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Summary generation failed: {str(e)}")
        return {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': str(e),
            'data': None
        }
    except Exception as e:
        logger.error(f"❌ Summary generation: Unexpected error: {str(e)}")
        return {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': str(e),
            'data': None
        }


def process_summary_task(candidate_slug, job_slug, task_metadata, updated_by=None):
    """
    Process a candidate summary task by testing endpoints and generating summary.
    Mirrors the UI flow from CandidateSummaryGenerator.jsx
    """
    
    logger.info(f"🚀 Starting summary generation for {candidate_slug} / {job_slug}")
    if updated_by:
        logger.info(f"👤 Triggered by: {updated_by.get('first_name')} {updated_by.get('last_name')} ({updated_by.get('email')})")
    
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
        }
    }
    
    # Step 1: Test Candidate Data (BLOCKING)
    candidate_test = test_endpoint('/api/test-candidate-data', candidate_slug, job_slug, 'Candidate Data')
    run_data['tests']['candidate_data'] = {
        'success': candidate_test['success'],
        'error': candidate_test['error']
    }
    
    if not candidate_test['success']:
        logger.error("❌ BLOCKING: Candidate data not found. Stopping.")
        run_data['generation'] = {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': 'Candidate data not found (blocking)'
        }
        log_to_firestore(run_data)
        return False, "Candidate data not found", run_data
    
    # Step 2: Test Job Data (BLOCKING)
    job_test = test_endpoint('/api/test-job-data', candidate_slug, job_slug, 'Job Data')
    run_data['tests']['job_data'] = {
        'success': job_test['success'],
        'error': job_test['error']
    }
    
    if not job_test['success']:
        logger.error("❌ BLOCKING: Job data not found. Stopping.")
        run_data['generation'] = {
            'success': False,
            'summary_length': 0,
            'duration_seconds': 0,
            'error': 'Job data not found (blocking)'
        }
        log_to_firestore(run_data)
        return False, "Job data not found", run_data
    
    # Step 3: Test CV Data (OPTIONAL)
    cv_test = test_endpoint('/api/test-cv-data', candidate_slug, job_slug, 'CV Data')
    run_data['tests']['cv_data'] = {
        'success': cv_test['success'],
        'error': cv_test['error']
    }
    if cv_test['success']:
        run_data['sources_used']['resume'] = True
    
    # Step 4: Test AI Interview (OPTIONAL)
    ai_test = test_endpoint('/api/test-ai-interview', candidate_slug, job_slug, 'AI Interview')
    run_data['tests']['ai_interview'] = {
        'success': ai_test['success'],
        'error': ai_test['error']
    }
    if ai_test['success']:
        run_data['sources_used']['anna_ai'] = True
    
    # Step 5: Test Quil Interview (OPTIONAL)
    quil_test = test_endpoint('/api/test-quil-interview', candidate_slug, job_slug, 'Quil Interview')
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
    
    # Log what sources we have
    sources = [k for k, v in run_data['sources_used'].items() if v]
    logger.info(f"📦 Available sources: {', '.join(sources) if sources else 'None'}")
    
    # Step 6: Generate Summary
    generation_result = generate_summary(candidate_slug, job_slug, DEFAULT_CONFIG)
    run_data['generation'] = generation_result
    
    # Log to Firestore
    firestore_id = log_to_firestore(run_data)
    
    # TODO: Send notification when complete
    # Options:
    # 1. Slack notification to #recruitment channel
    # 2. Email to updated_by user
    # 3. Webhook back to RecruitCRM (activity feed)
    # 
    # Implementation ideas:
    # - Success: "✅ Summary generated for {candidate_name} / {job_title}"
    # - Failure: "❌ Summary failed for {candidate_slug} - {error}"
    # - Include link to candidate in RecruitCRM
    # - Show sources used (Resume, Anna AI, Quil)
    # - Show generation time
    
    if generation_result['success']:
        logger.info(f"✅ Summary generation complete. Firestore ID: {firestore_id}")
        # TODO: send_slack_notification(updated_by, candidate_slug, job_slug, run_data)
        return True, "Summary generated successfully", run_data
    else:
        logger.error(f"❌ Summary generation failed: {generation_result['error']}")
        # TODO: send_slack_notification(updated_by, candidate_slug, job_slug, run_data, failed=True)
        return False, generation_result['error'], run_data


def summary_worker(request):
    """
    Cloud Function entry point.
    Triggered by Cloud Tasks queue.
    """
    
    logger.info("--- Summary Worker Invoked ---")
    
    # Validate method
    if request.method != 'POST':
        return jsonify({"error": "Method Not Allowed"}), 405
    
    try:
        # Parse task payload
        payload = request.get_json(silent=True)
        
        if not payload:
            logger.error("❌ No JSON payload received")
            return jsonify({"error": "Invalid payload"}), 400
        
        # Extract required fields
        candidate_slug = payload.get('candidate_slug')
        job_slug = payload.get('job_slug')
        
        # Extract optional updated_by from webhook payload
        webhook_payload = payload.get('webhook_payload', {})
        updated_by = webhook_payload.get('updated_by')
        
        if not candidate_slug or not job_slug:
            logger.error("❌ Missing required fields")
            return jsonify({
                "error": "Missing required fields",
                "required": ["candidate_slug", "job_slug"]
            }), 400
        
        # Extract task metadata
        task_metadata = {
            'cloud_task_id': request.headers.get('X-CloudTasks-TaskName', 'unknown'),
            'retry_attempt': int(request.headers.get('X-CloudTasks-TaskRetryCount', 0))
        }
        
        logger.info(f"📋 Processing task: {candidate_slug} / {job_slug}")
        logger.info(f"🔄 Retry attempt: {task_metadata['retry_attempt']}")
        
        # Process the task
        success, message, run_data = process_summary_task(
            candidate_slug,
            job_slug,
            task_metadata,
            updated_by
        )
            candidate_slug,
            job_slug,
            task_metadata
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
        logger.error(f"❌ Worker error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500
