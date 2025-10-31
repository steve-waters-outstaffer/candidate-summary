# orchestrator.py
# Contains the main business logic and orchestration for the summary task.

import time

# --- Import dependencies ---
from config import db, FALLBACK_CONFIG, WORKER_VERSION
from logging_helpers import logger, log_to_firestore
import api_client  # Import the entire module


def get_dynamic_config():
    """Fetch dynamic configuration from Firestore."""
    try:
        doc_ref = db.collection('webhook_config').document('default')
        doc = doc_ref.get()
        if doc.exists:
            config_data = doc.to_dict()
            logger.info("Fetched dynamic config from Firestore.")

            # --- REFACTORED: Map new Firestore field names ---
            # --- EDIT: Use .get on FALLBACK_CONFIG and provide a final default ---
            # This makes sure we get a value even if it's not in the fallback dict.
            fallback_stage_id = FALLBACK_CONFIG.get('target_stage_id', 726195)

            return {
                'use_quil': config_data.get('use_quil', FALLBACK_CONFIG['use_quil']),
                'include_fireflies': config_data.get('use_fireflies', FALLBACK_CONFIG['include_fireflies']),
                'proceed_without_interview': config_data.get('proceed_without_interview', FALLBACK_CONFIG['proceed_without_interview']),
                'additional_context': config_data.get('additional_context', FALLBACK_CONFIG['additional_context']),
                'prompt_type': config_data.get('default_prompt_id', FALLBACK_CONFIG['prompt_type']),

                # Use new clear names
                'push_summary_to_candidate': config_data.get('push_summary_to_candidate', FALLBACK_CONFIG['push_summary_to_candidate']),
                'create_tracking_note': config_data.get('create_tracking_note', FALLBACK_CONFIG['create_tracking_note']),
                'move_to_next_stage': config_data.get('move_to_next_stage', FALLBACK_CONFIG['move_to_next_stage']),

                'auto_push_delay_seconds': config_data.get('auto_push_delay_seconds', FALLBACK_CONFIG['auto_push_delay_seconds']),

                # --- EDIT: Add the new target_stage_id config value ---
                'target_stage_id': config_data.get('target_stage_id', fallback_stage_id)
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

    # --- Fetch dynamic config at the start of the process ---
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
        'post_actions': {
            'summary_push': None, # Renamed
            'note_creation': None,
            'stage_move': None # Renamed
        },
        'prompt_sources': {}
    }

    # --- Add top-level fields for easier querying in Firestore ---
    if updated_by:
        run_data['triggered_by_email'] = updated_by.get('email')
    run_data['success'] = False # Default to false, set to true on success
    run_data['prompt_id'] = dynamic_config.get('prompt_type')

    # Step 1: Test Candidate Data (BLOCKING)
    candidate_test = api_client.test_endpoint('/api/test-candidate', candidate_slug, job_slug, 'Candidate Data', method='POST')
    run_data['tests']['candidate_data'] = {
        'success': candidate_test['success'],
        'error': candidate_test['error']
    }
    if candidate_test['success'] and candidate_test['data']:
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
    job_test = api_client.test_endpoint('/api/test-job', candidate_slug, job_slug, 'Job Data', method='POST')
    run_data['tests']['job_data'] = {
        'success': job_test['success'],
        'error': job_test['error']
    }
    if job_test['success'] and job_test['data']:
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
    cv_test = api_client.test_endpoint('/api/test-resume', candidate_slug, job_slug, 'CV Data', method='POST')
    run_data['tests']['cv_data'] = {
        'success': cv_test['success'],
        'error': cv_test['error']
    }
    if cv_test['success']:
        run_data['sources_used']['resume'] = True

    # Step 4: Test AI Interview (OPTIONAL)
    ai_test = api_client.test_endpoint('/api/test-interview', candidate_slug, job_slug, 'AI Interview', method='POST')
    run_data['tests']['ai_interview'] = {
        'success': ai_test['success'],
        'error': ai_test['error']
    }
    if ai_test['success']:
        run_data['sources_used']['anna_ai'] = True

    # Step 5: Test Quil Interview (OPTIONAL)
    quil_test = api_client.test_endpoint('/api/test-quil', candidate_slug, job_slug, 'Quil Interview', method='POST')
    run_data['tests']['quil_interview'] = {
        'success': quil_test['success'],
        'error': quil_test['error']
    }
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

    # Check if we should proceed without interviews
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

    # Step 6: Generate Summary
    generation_result = api_client.generate_summary(candidate_slug, job_slug, dynamic_config)
    run_data['generation'] = generation_result
    run_data['success'] = generation_result['success'] # Update top-level success

    # Capture the sources confirmed by the generation endpoint
    prompt_sources = {}
    if generation_result.get('data'):
        raw_sources = generation_result['data'].get('sources_used') or {}
        if isinstance(raw_sources, dict):
            prompt_sources = {k: bool(v) for k, v in raw_sources.items()}
            run_data['prompt_sources'] = prompt_sources

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

    # --- THIS FIX IS WORKING ---
    if generation_result['success'] and generation_result['data']:
        run_data['summary_html'] = generation_result['data'].get('html_summary', '')

    # --- REFACTORED: Step 7: Post-Generation Actions ---
    if generation_result['success']:
        logger.info(
            "Summary generation complete. Checking post-actions...",
            extra={"json_fields": base_log_context}
        )

        # Action 1: Push Summary (using new flag and function name)
        if dynamic_config.get('push_summary_to_candidate'):
            push_result = api_client.handle_summary_push(
                candidate_slug,
                job_slug,
                run_data.get('summary_html', ''),
                updated_by
            )
            run_data['post_actions']['summary_push'] = push_result
        else:
            logger.info("Skipping summary push (disabled in config).", extra={"json_fields": base_log_context})

        # Action 2: Create Note (using new flag and new stub)
        if dynamic_config.get('create_tracking_note'):

            # --- FIX: Build the note as PLAIN TEXT ---
            # Get a list of sources that were successfully tested and used
            sources = [k.replace('_', ' ').title() for k, v in run_data['sources_used'].items() if v]
            trigger_email = (updated_by.get('email', 'Unknown') if updated_by else 'System')

            # Changed from HTML to plain text with newlines
            note_text = (
                "🤖 AI Summary Run - Report\n"
                f"Status: Success\n"
                f"Candidate: {run_data.get('candidate_name', 'N/A')}\n"
                f"Job: {run_data.get('job_name', 'N/A')}\n"
                f"Prompt Used: {run_data.get('prompt_id', 'unknown')}\n"
                f"Sources Used: {', '.join(sources) or 'None'}\n"
                f"Triggered by: {trigger_email}\n\n"
                "This is an automated note from the AI Summary Worker."
            )
            # --- End of note content ---

            note_result = api_client.handle_note_creation(
                candidate_slug,
                job_slug,
                note_text, # Pass the plain text
                updated_by
            )
            run_data['post_actions']['note_creation'] = note_result
        else:
            logger.info("Skipping note creation (disabled in config).", extra={"json_fields": base_log_context})

        # Action 3: Move Stage (using new flag and function name)
        if dynamic_config.get('move_to_next_stage'):

            # --- EDIT: Get the target_stage_id from config, with a fallback ---
            target_stage_id = dynamic_config.get('target_stage_id', 726195)

            push_result = api_client.handle_stage_move(
                candidate_slug,
                job_slug,
                target_stage_id,  # --- EDIT: Pass the ID here ---
                dynamic_config.get('auto_push_delay_seconds', 0),
                updated_by
            )
            run_data['post_actions']['stage_move'] = push_result
        else:
            logger.info("Skipping stage move (disabled in config).", extra={"json_fields": base_log_context})

    else:
        logger.error(
            f"Summary generation failed: {generation_result['error']}",
            extra={"json_fields": {**base_log_context, "error": generation_result['error']}}
        )

    # Step 8: Log final result
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
