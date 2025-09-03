# routes/bulk.py

import json
import re
from collections import defaultdict
from flask import Blueprint, request, jsonify, current_app
import uuid
import threading

# In-memory job store. For a production environment, you might replace this
# with a more persistent store like Redis or Firestore.
BULK_JOBS = {}

from config.prompts import build_full_prompt
from helpers import (
    fetch_recruitcrm_assigned_candidates,
    fetch_hiring_pipeline,
    fetch_recruitcrm_job,
    fetch_candidate_interview_id,
    fetch_alpharun_interview,
    upload_resume_to_gemini,
    generate_html_summary,
    fetch_recruitcrm_candidate_job_specific_fields,
    fetch_recruitcrm_candidate
)

bulk_bp = Blueprint('bulk_api', __name__)

def process_candidates_background(job_id, app_context):
    """
    This function runs in a background thread to process candidates
    without blocking the main request.
    """
    with app_context:
        job_details = BULK_JOBS[job_id]
        job_slug = job_details['job_slug']
        single_prompt = job_details['single_prompt']
        model = current_app.model

        try:
            job_data = fetch_recruitcrm_job(job_slug, include_custom_fields=True)
            if not job_data:
                job_details['status'] = 'failed'
                job_details['error'] = 'Could not fetch job data.'
                return

            job_details_data = job_data.get('data', job_data)
            alpharun_job_id = None
            for field in job_details_data.get('custom_fields', []):
                if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                    alpharun_job_id = field.get('value')
                    break

            for slug in job_details['candidate_slugs']:
                try:
                    full_candidate_data = fetch_recruitcrm_candidate(slug)
                    if not full_candidate_data:
                        raise Exception("Could not fetch candidate data.")

                    candidate_details_data = full_candidate_data.get('data', full_candidate_data)

                    job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(slug, job_slug)
                    if job_specific_fields:
                        if 'custom_fields' in candidate_details_data:
                            candidate_details_data['custom_fields'].extend(job_specific_fields.values())
                        else:
                            candidate_details_data['custom_fields'] = list(job_specific_fields.values())

                    gemini_resume_file = None
                    if candidate_details_data.get('resume'):
                        gemini_resume_file = upload_resume_to_gemini(candidate_details_data.get('resume'))

                    interview_data = None
                    if alpharun_job_id:
                        interview_id = fetch_candidate_interview_id(slug)
                        if interview_id:
                            interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)

                    summary = generate_html_summary(full_candidate_data, job_data, interview_data, "", single_prompt, None, gemini_resume_file, model)

                    if summary:
                        BULK_JOBS[job_id]['results'][slug] = {'status': 'success', 'summary': summary}
                    else:
                        raise Exception("AI failed to generate summary.")

                except Exception as e:
                    current_app.logger.error(f"Error processing candidate {slug} for job {job_id}: {e}")
                    BULK_JOBS[job_id]['results'][slug] = {'status': 'failed', 'error': str(e)}

                job_details['processed_count'] += 1

            job_details['status'] = 'complete'

        except Exception as e:
            current_app.logger.error(f"A fatal error occurred in background job {job_id}: {e}")
            job_details['status'] = 'failed'
            job_details['error'] = str(e)


@bulk_bp.route('/job-stages-with-counts/<job_slug>', methods=['GET'])
def get_job_stages_with_counts(job_slug):
    """Fetches all candidates for a job, counts them by stage, and returns a list of stages that have at least one candidate."""
    current_app.logger.info(f"\n--- Endpoint Hit: /api/job-stages-with-counts/{job_slug} ---")
    all_candidates = fetch_recruitcrm_assigned_candidates(job_slug)
    if not all_candidates:
        return jsonify({'error': 'No candidates found for this job or job not found.'}), 404

    stage_counts = defaultdict(int)
    for candidate_data in all_candidates:
        status_id = candidate_data.get('status', {}).get('status_id')
        if status_id:
            stage_counts[status_id] += 1

    pipeline = fetch_hiring_pipeline()
    if not pipeline:
        return jsonify({'error': 'Could not fetch the hiring pipeline.'}), 500

    stages_with_counts = []
    for stage in pipeline:
        count = stage_counts.get(stage['status_id'], 0)
        if count > 0:
            stage['candidate_count'] = count
            stages_with_counts.append(stage)

    return jsonify(stages_with_counts), 200

@bulk_bp.route('/candidates-in-stage/<job_slug>/<stage_id>', methods=['GET'])
def get_candidates_in_stage(job_slug, stage_id):
    """Fetches a list of candidates in a specific stage for a job."""
    current_app.logger.info(f"\n--- Endpoint Hit: /api/candidates-in-stage/{job_slug}/{stage_id} ---")
    candidates = fetch_recruitcrm_assigned_candidates(job_slug, status_id=stage_id)

    formatted_candidates = []
    for cand_info in candidates:
        candidate_data = cand_info.get('candidate', {})
        if candidate_data.get('slug'):
            formatted_candidates.append({
                'slug': candidate_data.get('slug'),
                'name': f"{candidate_data.get('first_name', '')} {candidate_data.get('last_name', '')}".strip()
            })

    return jsonify(formatted_candidates), 200

@bulk_bp.route('/bulk-process-job', methods=['POST'])
def start_bulk_process_job():
    """
    Starts an asynchronous job to process summaries for multiple candidates.
    Returns a job ID for polling the status.
    """
    current_app.logger.info("\n--- Endpoint Hit: /api/bulk-process-job (async) ---")
    data = request.get_json()
    job_url = data.get('job_url')
    single_prompt = data.get('single_candidate_prompt')
    candidate_slugs = data.get('candidate_slugs', [])

    if not all([job_url, single_prompt, candidate_slugs]):
        return jsonify({'error': 'Missing job_url, single_candidate_prompt, or candidate_slugs'}), 400

    job_id = str(uuid.uuid4())
    job_slug = job_url.split('/')[-1]

    BULK_JOBS[job_id] = {
        'status': 'processing',
        'job_slug': job_slug,
        'single_prompt': single_prompt,
        'candidate_slugs': candidate_slugs,
        'total_candidates': len(candidate_slugs),
        'processed_count': 0,
        'results': {slug: {'status': 'pending'} for slug in candidate_slugs},
        'email_html': None,
        'error': None
    }

    thread = threading.Thread(target=process_candidates_background, args=(job_id, current_app.app_context()))
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Job started', 'job_id': job_id}), 202

@bulk_bp.route('/bulk-job-status/<job_id>', methods=['GET'])
def get_bulk_job_status(job_id):
    """Pollable endpoint to get the status and results of a bulk processing job."""
    job = BULK_JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    response_data = {
        'status': job['status'],
        'total_candidates': job['total_candidates'],
        'processed_count': len([r for r in job['results'].values() if r['status'] != 'pending']),
        'failed_count': len([r for r in job['results'].values() if r['status'] == 'failed']),
        'results': job['results'],
        'email_html': job['email_html'],
        'error': job['error']
    }
    return jsonify(response_data), 200

@bulk_bp.route('/generate-bulk-email', methods=['POST'])
def generate_bulk_email():
    """Generates the final multi-candidate email from completed summaries."""
    current_app.logger.info("\n--- Endpoint Hit: /api/generate-bulk-email ---")
    data = request.get_json()
    job_id = data.get('job_id')
    multi_prompt = data.get('multi_candidate_prompt')

    if not all([job_id, multi_prompt]):
        return jsonify({'error': 'Missing job_id or multi_candidate_prompt'}), 400

    job = BULK_JOBS.get(job_id)
    if not job or job['status'] != 'complete':
        return jsonify({'error': 'Job not found or not yet complete'}), 404

    try:
        job_slug = job['job_slug']
        job_data = fetch_recruitcrm_job(job_slug, include_custom_fields=True)
        job_details = job_data.get('data', {}) if job_data else {}

        # We need the candidate names for the prompt
        all_candidates_in_job = fetch_recruitcrm_assigned_candidates(job_slug)
        candidate_name_map = {
            c.get('candidate', {}).get('slug'): f"{c.get('candidate', {}).get('first_name', '')} {c.get('candidate', {}).get('last_name', '')}".strip()
            for c in all_candidates_in_job
        }

        successful_summaries = {
            candidate_name_map.get(slug, slug): result['summary']
            for slug, result in job['results'].items()
            if result['status'] == 'success'
        }

        if not successful_summaries:
            return jsonify({'error': 'No successful summaries available to generate an email.'}), 400

        summaries_as_string = json.dumps(successful_summaries, indent=2)
        candidate_names_str = "\n".join(successful_summaries.keys())

        prompt_kwargs = {
            'client_name': data.get('client_name', job_details.get('company', {}).get('name', 'Valued Client')),
            'job_url': data.get('outstaffer_platform_url'),
            'job_title': job_details.get('name', ''),
            'job_data': job_details,
            'processed_summaries': summaries_as_string,
            'candidate_names': candidate_names_str,
            'preferred_candidate': data.get('preferred_candidate', ''),
            'additional_context': data.get('additional_context', '')
        }

        full_prompt = build_full_prompt(multi_prompt, "multiple", **prompt_kwargs)
        response = current_app.model.generate_content([full_prompt])

        if response and response.text:
            cleaned_content = re.sub(r'^```html\n|```$', '', response.text, flags=re.MULTILINE)
            link_url = data.get('outstaffer_platform_url') or f"https://app.recruitcrm.io/jobs/{job_slug}"
            email_html = cleaned_content.replace('[HERE_LINK]', f'<a href="{link_url}">here</a>')

            BULK_JOBS[job_id]['email_html'] = email_html
            return jsonify({'success': True, 'email_html': email_html}), 200
        else:
            raise Exception("AI model failed to generate email content.")

    except Exception as e:
        current_app.logger.error(f"Error generating bulk email for job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500