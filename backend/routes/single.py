# routes/single.py

import datetime
import re
from flask import Blueprint, request, jsonify, current_app
import structlog
import requests

from config.prompts import get_available_prompts
from helpers.ai_helpers import (
    generate_html_summary,
    upload_resume_to_gemini,
)
from helpers.fireflies_helpers import (
    extract_fireflies_transcript_id,
    fetch_fireflies_transcript,
    normalise_fireflies_transcript,
)
from helpers.recruitcrm_helpers import (
    fetch_alpharun_interview,
    fetch_candidate_interview_id,
    fetch_recruitcrm_candidate,
    fetch_recruitcrm_candidate_job_specific_fields,
    fetch_recruitcrm_job,
    get_recruitcrm_headers,
)

log = structlog.get_logger()


single_bp = Blueprint('single_api', __name__)

@single_bp.route('/prompts', methods=['GET'])
def list_prompts():
    """Returns a list of available prompt configurations."""
    category = request.args.get('category', 'single')
    log.info("single.list_prompts.called", category=category)
    try:
        prompts = get_available_prompts(category)
        return jsonify(prompts), 200
    except Exception as e:
        log.error("single.prompts.error", error=str(e))
        return jsonify({'error': 'Could not retrieve prompt list from server'}), 500

@single_bp.route('/test-candidate', methods=['POST'])
def test_candidate():
    """Tests the connection to the RecruitCRM candidate API."""
    data = request.get_json()
    slug = data.get('candidate_slug')
    log.info("single.test_candidate.called", candidate_slug=slug)
    if not slug:
        return jsonify({'error': 'Missing candidate_slug'}), 400

    response_data = fetch_recruitcrm_candidate(slug)
    if response_data:
        candidate_details = response_data.get('data', response_data)
        interview_id = None
        for field in candidate_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Interview ID':
                raw_interview_id = field.get('value')
                if raw_interview_id:
                    interview_id = raw_interview_id.split('?')[0]
                break
        return jsonify({
            'success': True,
            'message': 'Candidate confirmed',
            'candidate_name': f"{candidate_details.get('first_name', '')} {candidate_details.get('last_name', '')}".strip(),
            'interview_id': interview_id
        })
    return jsonify({'error': 'Failed to fetch candidate data'}), 404

@single_bp.route('/test-job', methods=['POST'])
def test_job():
    """Tests the connection to the RecruitCRM job API."""
    data = request.get_json()
    slug = data.get('job_slug')
    log.info("single.test_job.called", job_slug=slug)
    if not slug:
        return jsonify({'error': 'Missing job_slug'}), 400

    response_data = fetch_recruitcrm_job(slug)
    if response_data:
        job_details = response_data.get('data', response_data)
        alpharun_job_id = None
        for field in job_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                alpharun_job_id = field.get('value')
                break
        return jsonify({
            'success': True,
            'message': 'Job confirmed',
            'job_name': job_details.get('name', 'Unknown Job'),
            'alpharun_job_id': alpharun_job_id
        })
    return jsonify({'error': 'Failed to fetch job data'}), 404

@single_bp.route('/test-interview', methods=['POST'])
def test_interview():
    """Tests the connection to the AlphaRun interview API."""
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
    job_slug = data.get('job_slug')
    log.info("single.test_interview.called", candidate_slug=candidate_slug, job_slug=job_slug)

    if not candidate_slug or not job_slug:
        return jsonify({'error': 'Missing candidate_slug or job_slug'}), 400

    # Obtain the interview ID from RecruitCRM, checking job-associated fields first
    interview_id = fetch_candidate_interview_id(candidate_slug, job_slug)
    if not interview_id:
        return jsonify({'error': 'No AI Interview ID found for this candidate and job'}), 404

    # Fetch the AlphaRun job ID from the job's custom fields
    job_data = fetch_recruitcrm_job(job_slug)
    alpharun_job_id = None
    if job_data:
        job_details = job_data.get('data', job_data)
        for field in job_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                alpharun_job_id = field.get('value')
                break

    if not alpharun_job_id:
        return jsonify({'error': 'AlphaRun job ID not found for this job'}), 404

    interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)

    if interview_data:
        contact = interview_data.get('data', {}).get('interview', {}).get('contact', {})
        return jsonify({
            'success': True,
            'message': 'Interview confirmed',
            'candidate_name': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            'interview_id': interview_id,
            'alpharun_job_id': alpharun_job_id
        })
    return jsonify({'error': 'Failed to fetch interview data'}), 404

@single_bp.route('/test-fireflies', methods=['POST'])
def test_fireflies():
    """Tests the connection to the Fireflies API and returns the meeting title."""
    data = request.get_json()
    transcript_url = data.get('fireflies_url') or data.get('transcript_url')
    log.info("single.test_fireflies.called", transcript_url=transcript_url)

    if not transcript_url:
        return jsonify({'error': 'Missing fireflies_url or transcript_url'}), 400

    transcript_id = extract_fireflies_transcript_id(transcript_url)
    if not transcript_id:
        return jsonify({'error': 'Invalid Fireflies URL or Transcript ID'}), 400

    transcript_data = fetch_fireflies_transcript(transcript_id)
    if transcript_data:
        return jsonify({
            'success': True,
            'message': 'Transcript confirmed',
            'meeting_title': transcript_data.get('title', 'Unknown Title')
        })
    return jsonify({'error': 'Failed to fetch transcript data from Fireflies.ai'}), 404

@single_bp.route('/test-resume', methods=['POST'])
def test_resume():
    """Checks for the presence of a resume in the candidate data."""
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
    log.info("single.test_resume.called", candidate_slug=candidate_slug)
    if not candidate_slug:
        return jsonify({'error': 'Missing candidate_slug'}), 400

    candidate_data = fetch_recruitcrm_candidate(candidate_slug)
    if candidate_data:
        candidate_details = candidate_data.get('data', candidate_data)
        resume_info = candidate_details.get('resume')
        if resume_info and (resume_info.get('url') or resume_info.get('file_link')):
            return jsonify({
                'success': True,
                'message': 'Resume Found',
                'resume_name': resume_info.get('filename')
            })
        else:
            return jsonify({'success': False, 'message': 'No resume on file for this candidate.'})
    return jsonify({'error': 'Failed to fetch candidate data to check for resume'}), 404

@single_bp.route('/generate-summary', methods=['POST'])
def generate_summary():
    """Generate candidate summary, optionally including Fireflies and interview data."""
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
    job_slug = data.get('job_slug')
    fireflies_url = data.get('fireflies_url')
    prompt_type = data.get('prompt_type', 'recruitment.detailed')
    log.info("single.generate_summary.called", candidate_slug=candidate_slug, job_slug=job_slug, fireflies_url=fireflies_url, prompt_type=prompt_type)

    try:
        additional_context = data.get('additional_context', '')
        model = current_app.model

        if not all([candidate_slug, job_slug]):
            return jsonify({'error': 'Missing required RecruitCRM fields'}), 400

        candidate_data = fetch_recruitcrm_candidate(candidate_slug)
        job_data = fetch_recruitcrm_job(job_slug, include_custom_fields=True) # Ensure custom fields are included

        if not candidate_data or not job_data:
            missing = [name for name, d in [("candidate", candidate_data), ("job", job_data)] if not d]
            return jsonify({'error': f'Failed to fetch data from: {", ".join(missing)}'}), 500

        # Combine candidate's general custom fields with job-specific ones
        job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug)
        if candidate_data and job_specific_fields:
            candidate_details = candidate_data.get('data', candidate_data)
            if 'custom_fields' in candidate_details:
                candidate_details['custom_fields'].extend(job_specific_fields.values())
            else:
                candidate_details['custom_fields'] = list(job_specific_fields.values())

        # --- AI INTERVIEW LOGIC ---
        interview_data = None
        alpharun_job_id = None

        # 1. Get Alpharun Job ID from the job's custom fields
        job_details = job_data.get('data', job_data)
        for field in job_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                alpharun_job_id = field.get('value')
                break

        # 2. If we have an Alpharun Job ID, fetch the interview using the new fallback logic
        if alpharun_job_id:
            interview_id = fetch_candidate_interview_id(candidate_slug, job_slug)
            if interview_id:
                interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)
        # --- END AI INTERVIEW LOGIC ---

        gemini_resume_file = None
        if candidate_data:
            candidate_details = candidate_data.get('data', candidate_data)
            resume_info = candidate_details.get('resume')
            if resume_info:
                gemini_resume_file = upload_resume_to_gemini(resume_info)

        fireflies_data = None
        if fireflies_url:
            transcript_id = extract_fireflies_transcript_id(fireflies_url)
            if transcript_id:
                raw_transcript = fetch_fireflies_transcript(transcript_id)
                if raw_transcript:
                    fireflies_data = normalise_fireflies_transcript(raw_transcript)

        html_summary = generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data, gemini_resume_file, model)

        if html_summary:
            return jsonify({'success': True, 'html_summary': html_summary, 'candidate_slug': candidate_slug})
        else:
            return jsonify({'error': 'Failed to generate summary from AI model'}), 500

    except Exception as e:
        log.error("single.generate_summary.error", error=str(e))
        return jsonify({'error': str(e)}), 500

@single_bp.route('/push-to-recruitcrm', methods=['POST'])
def push_to_recruitcrm():
    """Push generated summary to RecruitCRM candidate record"""
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
    html_summary = data.get('html_summary')
    log.info(
        "single.push_to_recruitcrm.called",
        candidate_slug=candidate_slug,
        html_length=len(html_summary) if html_summary else 0,
    )
    try:
        if not candidate_slug or not html_summary:
            log.error("single.push_to_recruitcrm.missing_data")
            return jsonify({'error': 'Missing candidate slug or HTML summary'}), 400

        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {'candidate_summary': (None, html_summary)}
        log.info("single.push_to_recruitcrm.request.sent", url=url)

        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        log.info("single.push_to_recruitcrm.response", status=response.status_code)

        if response.status_code == 200:
            log.info("single.push_to_recruitcrm.success")
            return jsonify({'success': True, 'message': 'Summary pushed to RecruitCRM successfully'})
        else:
            log.error("single.push_to_recruitcrm.failed", status=response.status_code)
            return jsonify({'error': f'Failed to update RecruitCRM: {response.text}'}), 500

    except Exception as e:
        log.error("single.push_to_recruitcrm.exception", error=str(e))
        return jsonify({'error': str(e)}), 500

@single_bp.route('/log-feedback', methods=['POST'])
def log_feedback():
    """Receives and logs user feedback on a generated summary to Firestore."""
    data = request.get_json()
    log.info("single.log_feedback.called", has_rating=data.get('rating') is not None, has_comments=bool(data.get('comments')))
    db = current_app.db
    if not db:
        return jsonify({'error': 'Firestore is not configured on the server'}), 500
    try:
        feedback_data = {
            'rating': data.get('rating'),
            'comments': data.get('comments', ''),
            'prompt_type': data.get('prompt_type'),
            'generated_summary_html': data.get('generated_summary_html'),
            'candidate_slug': data.get('candidate_slug'),
            'job_slug': data.get('job_slug'),
            'timestamp': datetime.datetime.utcnow()
        }
        feedback_ref = db.collection('feedback').document()
        feedback_ref.set(feedback_data)
        return jsonify({'success': True, 'message': 'Feedback logged successfully'}), 200
    except Exception as e:
        log.error("single.log_feedback.error", error=str(e))
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500