# routes/single.py

import datetime
import re
from flask import Blueprint, request, jsonify, current_app

from config.prompts import get_available_prompts
from helpers import (
    fetch_recruitcrm_candidate,
    fetch_recruitcrm_job,
    fetch_alpharun_interview,
    extract_fireflies_transcript_id,
    fetch_fireflies_transcript,
    normalise_fireflies_transcript,
    upload_resume_to_gemini,
    generate_html_summary,
    get_recruitcrm_headers,
    fetch_recruitcrm_candidate_job_specific_fields
)
import requests

single_bp = Blueprint('single_api', __name__)

@single_bp.route('/prompts', methods=['GET'])
def list_prompts():
    """Returns a list of available prompt configurations."""
    current_app.logger.info("\n--- Endpoint Hit: /api/prompts ---")
    try:
        category = request.args.get('category', 'single')  # Default to single
        prompts = get_available_prompts(category)
        return jsonify(prompts), 200
    except Exception as e:
        current_app.logger.error(f"!!! EXCEPTION in list_prompts: {e}")
        return jsonify({'error': 'Could not retrieve prompt list from server'}), 500

@single_bp.route('/test-candidate', methods=['POST'])
def test_candidate():
    """Tests the connection to the RecruitCRM candidate API."""
    current_app.logger.info("\n--- Endpoint Hit: /api/test-candidate ---")
    data = request.get_json()
    slug = data.get('candidate_slug')
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
    current_app.logger.info("\n--- Endpoint Hit: /api/test-job ---")
    data = request.get_json()
    slug = data.get('job_slug')
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
    current_app.logger.info("\n--- Endpoint Hit: /api/test-interview ---")
    data = request.get_json()
    raw_interview_id = data.get('interview_id')
    job_opening_id = data.get('alpharun_job_id')
    if not raw_interview_id or not job_opening_id:
        return jsonify({'error': 'Missing interview_id or alpharun_job_id'}), 400

    interview_id = raw_interview_id.split('?')[0]
    interview_data = fetch_alpharun_interview(job_opening_id, interview_id)
    if interview_data:
        contact = interview_data.get('data', {}).get('interview', {}).get('contact', {})
        return jsonify({
            'success': True, 'message': 'Interview confirmed',
            'candidate_name': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        })
    return jsonify({'error': 'Failed to fetch interview data'}), 404

@single_bp.route('/test-fireflies', methods=['POST'])
def test_fireflies():
    """Tests the connection to the Fireflies API and returns the meeting title."""
    current_app.logger.info("\n--- Endpoint Hit: /api/test-fireflies ---")
    data = request.get_json()
    transcript_url = data.get('transcript_url')
    if not transcript_url:
        return jsonify({'error': 'Missing transcript_url'}), 400

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
    current_app.logger.info("\n--- Endpoint Hit: /api/test-resume ---")
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')
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
    current_app.logger.info("\n--- Endpoint Hit: /api/generate-summary ---")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        job_slug = data.get('job_slug')
        alpharun_job_id = data.get('alpharun_job_id')
        raw_interview_id = data.get('interview_id')
        fireflies_url = data.get('fireflies_url')
        additional_context = data.get('additional_context', '')
        prompt_type = data.get('prompt_type', 'recruitment.detailed')
        model = current_app.model

        interview_id = raw_interview_id.split('?')[0] if raw_interview_id else None

        if not all([candidate_slug, job_slug]):
            return jsonify({'error': 'Missing required RecruitCRM fields'}), 400

        candidate_data = fetch_recruitcrm_candidate(candidate_slug)
        job_data = fetch_recruitcrm_job(job_slug)

        job_specific_fields = fetch_recruitcrm_candidate_job_specific_fields(candidate_slug, job_slug)
        if candidate_data and job_specific_fields:
            if 'data' in candidate_data and 'custom_fields' in candidate_data['data']:
                candidate_data['data']['custom_fields'].extend(job_specific_fields)
            else:
                candidate_data.setdefault('data', {})['custom_fields'] = job_specific_fields

        interview_data = None
        if alpharun_job_id and interview_id:
            interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)

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

        if not all([candidate_data, job_data]):
            missing = [name for name, d in [("candidate", candidate_data), ("job", job_data)] if not d]
            return jsonify({'error': f'Failed to fetch data from: {", ".join(missing)}'}), 500

        html_summary = generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data, gemini_resume_file, model)

        if html_summary:
            return jsonify({'success': True, 'html_summary': html_summary, 'candidate_slug': candidate_slug})
        else:
            return jsonify({'error': 'Failed to generate summary from AI model'}), 500

    except Exception as e:
        current_app.logger.error(f"!!! TOP-LEVEL EXCEPTION in generate_summary: {e}")
        return jsonify({'error': str(e)}), 500

@single_bp.route('/push-to-recruitcrm', methods=['POST'])
def push_to_recruitcrm():
    """Push generated summary to RecruitCRM candidate record"""
    current_app.logger.info("\n--- Endpoint Hit: /api/push-to-recruitcrm ---")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        html_summary = data.get('html_summary')
        current_app.logger.info(f"Candidate slug: {candidate_slug}, HTML length: {len(html_summary) if html_summary else 0}")

        if not candidate_slug or not html_summary:
            current_app.logger.error("Missing candidate slug or HTML summary")
            return jsonify({'error': 'Missing candidate slug or HTML summary'}), 400

        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {'candidate_summary': (None, html_summary)}
        current_app.logger.info(f"Making request to: {url}")

        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        current_app.logger.info(f"RecruitCRM response status: {response.status_code}")

        if response.status_code == 200:
            current_app.logger.info("SUCCESS: Summary pushed to RecruitCRM")
            return jsonify({'success': True, 'message': 'Summary pushed to RecruitCRM successfully'})
        else:
            current_app.logger.error(f"!!! ERROR: Failed to update RecruitCRM: {response.text}")
            return jsonify({'error': f'Failed to update RecruitCRM: {response.text}'}), 500

    except Exception as e:
        current_app.logger.error(f"!!! TOP-LEVEL EXCEPTION in push_to_recruitcrm: {e}")
        return jsonify({'error': str(e)}), 500

@single_bp.route('/log-feedback', methods=['POST'])
def log_feedback():
    """Receives and logs user feedback on a generated summary to Firestore."""
    current_app.logger.info("\n--- Endpoint Hit: /api/log-feedback ---")
    db = current_app.db
    if not db:
        return jsonify({'error': 'Firestore is not configured on the server'}), 500
    try:
        data = request.get_json()
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
        current_app.logger.error(f"!!! EXCEPTION in log_feedback: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500