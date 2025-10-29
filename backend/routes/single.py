# routes/single.py

import datetime
import re
from flask import Blueprint, request, jsonify, current_app
import structlog
import requests

# --- Start Debugging Imports ---
log = structlog.get_logger()
log.info("routes.single: Top of file, starting imports.")

try:
    log.info("routes.single: Importing from config.prompts...")
    from config.prompts import get_available_prompts
    log.info("routes.single: Successfully imported from config.prompts.")

    log.info("routes.single: Importing from helpers.recruitcrm_helpers...")
    from helpers.recruitcrm_helpers import (
        fetch_recruitcrm_candidate,
        fetch_recruitcrm_job,
        fetch_alpharun_interview,
        get_recruitcrm_headers,
        fetch_recruitcrm_candidate_job_specific_fields,
        fetch_candidate_interview_id,
        fetch_candidate_notes
    )
    log.info("routes.single: Successfully imported from helpers.recruitcrm_helpers.")

    log.info("routes.single: Importing from helpers.quil_helpers...")
    from helpers.quil_helpers import get_quil_interview_for_job
    log.info("routes.single: Successfully imported from helpers.quil_helpers.")

    log.info("routes.single: Importing from helpers.fireflies_helpers...")
    from helpers.fireflies_helpers import (
        extract_fireflies_transcript_id,
        fetch_fireflies_transcript,
        normalise_fireflies_transcript
    )
    log.info("routes.single: Successfully imported from helpers.fireflies_helpers.")

    log.info("routes.single: Importing from helpers.ai_helpers...")
    from helpers.ai_helpers import (
        upload_resume_to_gemini,
        generate_html_summary
    )
    log.info("routes.single: Successfully imported from helpers.ai_helpers.")

    log.info("routes.single: Importing from helpers.gmail_helpers...")
    from helpers.gmail_helpers import create_gmail_draft
    log.info("routes.single: Successfully imported from helpers.gmail_helpers.")

except Exception as e:
    log.error("routes.single: FAILED during import", error=str(e), exc_info=True)
    import sys
    sys.exit(1)

log.info("routes.single: All imports successful.")
# --- End Debugging Imports ---


single_bp = Blueprint('single_api', __name__)

@single_bp.route('/prompts', methods=['GET'])
def list_prompts():
    """Returns a list of available prompt configurations."""
    log.info("single.prompts.hit")
    try:
        category = request.args.get('category', 'single')  # Default to single
        prompt_type = request.args.get('type')  # Optional: 'email' or 'summary'
        prompts = get_available_prompts(category, prompt_type)
        return jsonify(prompts), 200
    except Exception as e:
        log.error("single.prompts.error", error=str(e))
        return jsonify({'error': 'Could not retrieve prompt list from server'}), 500

@single_bp.route('/test-candidate', methods=['POST'])
def test_candidate():
    """Tests the connection to the RecruitCRM candidate API."""
    log.info("single.test_candidate.hit")
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
    log.info("single.test_job.hit")
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
    log.info("single.test_interview.hit")
    data = request.get_json()

    candidate_slug = data.get('candidate_slug')
    job_slug = data.get('job_slug')

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
    log.info("single.test_fireflies.hit")
    data = request.get_json()

    # Check for both 'fireflies_url' and 'transcript_url' to handle inconsistency
    transcript_url = data.get('fireflies_url') or data.get('transcript_url')

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

@single_bp.route('/test-quil', methods=['POST'])
def test_quil():
    """Tests Quil note detection and matching for a candidate and job."""
    log.info("single.test_quil.hit")
    data = request.get_json()
    
    candidate_slug = data.get('candidate_slug')
    job_slug = data.get('job_slug')
    
    if not candidate_slug or not job_slug:
        return jsonify({'error': 'Missing candidate_slug or job_slug'}), 400
    
    try:
        # Fetch candidate notes
        candidate_notes = fetch_candidate_notes(candidate_slug)
        log.info("single.test_quil.fetched_notes", 
                 note_count=len(candidate_notes) if candidate_notes else 0,
                 notes_type=type(candidate_notes).__name__)
        
        if not candidate_notes:
            return jsonify({'error': 'No notes found for candidate'}), 404
        
        # Count Quil notes
        quil_notes = [n for n in candidate_notes if n.get('description', '').startswith('Quil ')]
        log.info("single.test_quil.filtered_quil_notes",
                 quil_count=len(quil_notes),
                 quil_type=type(quil_notes).__name__)
        
        if not quil_notes:
            return jsonify({'error': 'No Quil interview notes found for this candidate'}), 404
        
        # Fetch job details for matching
        job_data = fetch_recruitcrm_job(job_slug)
        if not job_data:
            return jsonify({'error': 'Failed to fetch job data'}), 404
        
        job_details = job_data.get('data', job_data)
        job_title = job_details.get('name', 'Unknown Job')
        job_description = job_details.get('description', '')
        
        # Get matched Quil note
        log.info("single.test_quil.calling_get_quil_interview",
                 candidate_notes_type=type(candidate_notes).__name__,
                 job_slug=job_slug)
        quil_data = get_quil_interview_for_job(
            candidate_notes,
            job_slug,
            job_title,
            job_description
        )
        log.info("single.test_quil.got_quil_data",
                 quil_data_type=type(quil_data).__name__ if quil_data else "None")
        
        if quil_data:
            return jsonify({
                'success': True,
                'message': 'Quil interview notes found and matched',
                'quil_notes_count': len(quil_notes),
                'matched_date': quil_data.get('date'),
                'matched_title': quil_data.get('title'),
                'has_summary': bool(quil_data.get('summary_html')),
                'has_url': bool(quil_data.get('quil_url'))
            })
        else:
            return jsonify({'error': 'Quil notes found but matching failed'}), 500
            
    except Exception as e:
        log.error("single.test_quil.error", error=str(e), exc_info=True)
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@single_bp.route('/test-resume', methods=['POST'])
def test_resume():
    """Checks for the presence of a resume in the candidate data."""
    log.info("single.test_resume.hit")
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
    log.info("single.generate_summary.hit")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        job_slug = data.get('job_slug')
        fireflies_url = data.get('fireflies_url')
        additional_context = data.get('additional_context', '')
        prompt_type = data.get('prompt_type', 'recruitment.detailed')
        client = current_app.client

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
                gemini_resume_file = upload_resume_to_gemini(resume_info, client)

        # --- QUIL INTERVIEW LOGIC ---
        quil_data = None
        use_quil = data.get('use_quil', False)
        if use_quil and candidate_slug and job_slug:
            log.info("single.generate_summary.fetching_quil", 
                     candidate_slug=candidate_slug, 
                     job_slug=job_slug)
            try:
                candidate_notes = fetch_candidate_notes(candidate_slug)
                job_title = job_details.get('name', 'Unknown Job')
                job_description = job_details.get('description', '')
                
                quil_data = get_quil_interview_for_job(
                    candidate_notes,
                    job_slug,
                    job_title,
                    job_description
                )
                
                if quil_data:
                    log.info("single.generate_summary.quil_found", 
                             has_summary=bool(quil_data.get('summary_html')))
                else:
                    log.warning("single.generate_summary.quil_not_found")
            except Exception as e:
                log.error("single.generate_summary.quil_error", error=str(e))
        # --- END QUIL INTERVIEW LOGIC ---

        fireflies_data = None
        if fireflies_url:
            transcript_id = extract_fireflies_transcript_id(fireflies_url)
            if transcript_id:
                raw_transcript = fetch_fireflies_transcript(transcript_id)
                if raw_transcript:
                    fireflies_data = normalise_fireflies_transcript(raw_transcript)

        # Track which sources will be sent to the prompt/generation step
        prompt_sources = {
            'resume': bool(gemini_resume_file),
            'anna_ai': bool(interview_data),
            'quil': bool(quil_data and quil_data.get('summary_html')),
            'fireflies': bool(fireflies_data),
            'additional_context': bool(additional_context.strip()) if isinstance(additional_context, str) else bool(additional_context)
        }

        log.info(
            "single.generate_summary.prompt_sources",
            candidate_slug=candidate_slug,
            job_slug=job_slug,
            prompt_type=prompt_type,
            sources_used=prompt_sources
        )

        if prompt_sources['quil']:
            log.info(
                "single.generate_summary.using_quil_summary",
                candidate_slug=candidate_slug,
                job_slug=job_slug,
                prompt_type=prompt_type,
                quil_summary_present=True
            )

        html_summary = generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data, quil_data, gemini_resume_file, client)

        if html_summary:
            return jsonify({
                'success': True,
                'html_summary': html_summary,
                'candidate_slug': candidate_slug,
                'sources_used': prompt_sources,
                'quil_summary_used': prompt_sources['quil']
            })
        else:
            return jsonify({'error': 'Failed to generate summary from AI model'}), 500

    except Exception as e:
        log.error("single.generate_summary.error", error=str(e))
        return jsonify({'error': str(e)}), 500

@single_bp.route('/push-to-recruitcrm', methods=['POST'])
def push_to_recruitcrm():
    """Push generated summary to RecruitCRM candidate record"""
    log.info("single.push_to_recruitcrm.hit")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        html_summary = data.get('html_summary')
        log.info(
            "single.push_to_recruitcrm.request",
            candidate_slug=candidate_slug,
            html_length=len(html_summary) if html_summary else 0,
        )

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

@single_bp.route('/create-gmail-draft', methods=['POST'])
def create_gmail_draft_route():
    """Create a Gmail draft from generated email content"""
    log.info("single.create_gmail_draft.hit")
    try:
        data = request.get_json()
        user_access_token = data.get('access_token')
        subject = data.get('subject')
        html_body = data.get('html_body')
        to_email = data.get('to_email')  # Optional
        
        # Get refresh credentials for automatic token refresh
        refresh_token = data.get('refresh_token')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        # Get summary HTML for PDF generation
        summary_html = data.get('summary_html')
        pdf_filename = data.get('pdf_filename')
        
        if not all([user_access_token, subject, html_body]):
            log.error("single.create_gmail_draft.missing_data")
            return jsonify({'error': 'Missing required fields: access_token, subject, html_body'}), 400
        
        result = create_gmail_draft(
            user_access_token, 
            subject, 
            html_body, 
            to_email,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            summary_html=summary_html,
            pdf_filename=pdf_filename
        )
        
        if result['success']:
            log.info("single.create_gmail_draft.success", draft_id=result['draft_id'], pdf_generated=result.get('pdf_generated', False))
            return jsonify(result), 200
        else:
            log.error("single.create_gmail_draft.failed", error=result.get('error'))
            return jsonify({'error': result.get('error', 'Failed to create Gmail draft')}), 500
            
    except Exception as e:
        log.error("single.create_gmail_draft.exception", error=str(e))
        return jsonify({'error': str(e)}), 500

@single_bp.route('/log-feedback', methods=['POST'])
def log_feedback():
    """Receives and logs user feedback on a generated summary to Firestore."""
    log.info("single.log_feedback.hit")
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
        log.error("single.log_feedback.error", error=str(e))
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500