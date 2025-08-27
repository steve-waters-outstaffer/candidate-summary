import os
import logging
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from collections import defaultdict
# Load environment variables from a .env file
load_dotenv()
import google.generativeai as genai
from google.cloud import firestore
from config.prompts import build_full_prompt, get_available_prompts
import datetime

# Import all helper functions
from helpers import (
    fetch_recruitcrm_candidate,
    fetch_recruitcrm_job,
    fetch_alpharun_interview,
    extract_fireflies_transcript_id,
    fetch_fireflies_transcript,
    normalise_fireflies_transcript,
    upload_resume_to_gemini,
    generate_html_summary,
    generate_ai_response,
    get_recruitcrm_headers,
    fetch_recruitcrm_assigned_candidates,
    fetch_hiring_pipeline
)

# ==============================================================================
# 1. INITIALIZATION & CONFIGURATION
# ==============================================================================

# Load environment variables from a .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# --- CORS configuration ---
CORS(app,
     origins=[
         "https://candidate-summary-ai.web.app",  # Deployed frontend
         "http://localhost:5173",                 # Local development (Vite)
         "http://localhost:3000"                  # Local development (Create React App)
     ],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True
     )

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)

# --- Environment Variable Checks ---
RECRUITCRM_API_KEY = os.getenv('RECRUITCRM_API_KEY')
ALPHARUN_API_KEY = os.getenv('ALPHARUN_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
FIREFLIES_API_KEY = os.getenv('FIREFLIES_API_KEY')

if not RECRUITCRM_API_KEY:
    app.logger.error("!!! FATAL ERROR: RECRUITCRM_API_KEY environment variable is not set.")
if not ALPHARUN_API_KEY:
    app.logger.error("!!! FATAL ERROR: ALPHARUN_API_KEY environment variable is not set.")
if not GOOGLE_API_KEY:
    app.logger.error("!!! FATAL ERROR: GOOGLE_API_KEY environment variable is not set.")
if not FIREFLIES_API_KEY:
    app.logger.error("!!! FATAL ERROR: FIREFLIES_API_KEY environment variable is not set.")

# Configure Google Gemini
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    app.logger.info("LOG: Google Gemini configured successfully.")
except Exception as e:
    app.logger.error(f"!!! FATAL ERROR: Could not configure Google Gemini: {e}")
    model = None

# --- Firestore Configuration ---
try:
    db = firestore.Client()
    app.logger.info("LOG: Firestore client initialized successfully.")
except Exception as e:
    app.logger.error(f"!!! FATAL ERROR: Could not initialize Firestore client: {e}")
    db = None

# ==============================================================================
# 2. FLASK API ROUTES
# ==============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint to confirm the server is running."""
    app.logger.info("LOG: Health check endpoint was hit.")
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/prompts', methods=['GET'])
def list_prompts():
    """Returns a list of available prompt configurations."""
    app.logger.info("\n--- Endpoint Hit: /api/prompts ---")
    try:
        category = request.args.get('category', 'single')  # Default to single
        prompts = get_available_prompts(category)
        return jsonify(prompts), 200
    except Exception as e:
        app.logger.error(f"!!! EXCEPTION in list_prompts: {e}")
        return jsonify({'error': 'Could not retrieve prompt list from server'}), 500

@app.route('/api/job-stages-with-counts/<job_slug>', methods=['GET'])
def get_job_stages_with_counts(job_slug):
    """
    Fetches all candidates for a job, counts them by stage, and returns
    a list of stages that have at least one candidate.
    """
    app.logger.info(f"\n--- Endpoint Hit: /api/job-stages-with-counts/{job_slug} ---")

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


@app.route('/api/test-candidate', methods=['POST'])
def test_candidate():
    """Tests the connection to the RecruitCRM candidate API."""
    app.logger.info("\n--- Endpoint Hit: /api/test-candidate ---")
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

@app.route('/api/test-job', methods=['POST'])
def test_job():
    """Tests the connection to the RecruitCRM job API."""
    app.logger.info("\n--- Endpoint Hit: /api/test-job ---")
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

@app.route('/api/test-interview', methods=['POST'])
def test_interview():
    """Tests the connection to the AlphaRun interview API."""
    app.logger.info("\n--- Endpoint Hit: /api/test-interview ---")
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

@app.route('/api/test-fireflies', methods=['POST'])
def test_fireflies():
    """Tests the connection to the Fireflies API and returns the meeting title."""
    app.logger.info("\n--- Endpoint Hit: /api/test-fireflies ---")
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

@app.route('/api/test-resume', methods=['POST'])
def test_resume():
    """Checks for the presence of a resume in the candidate data."""
    app.logger.info("\n--- Endpoint Hit: /api/test-resume ---")
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

@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    """Generate candidate summary, optionally including Fireflies and interview data."""
    app.logger.info("\n--- Endpoint Hit: /api/generate-summary ---")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        job_slug = data.get('job_slug')
        alpharun_job_id = data.get('alpharun_job_id')
        raw_interview_id = data.get('interview_id')
        fireflies_url = data.get('fireflies_url')
        additional_context = data.get('additional_context', '')
        prompt_type = data.get('prompt_type', 'recruitment.detailed')

        interview_id = raw_interview_id.split('?')[0] if raw_interview_id else None

        if not all([candidate_slug, job_slug]):
            return jsonify({'error': 'Missing required RecruitCRM fields'}), 400

        candidate_data = fetch_recruitcrm_candidate(candidate_slug)
        job_data = fetch_recruitcrm_job(job_slug)

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
        app.logger.error(f"!!! TOP-LEVEL EXCEPTION in generate_summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/push-to-recruitcrm', methods=['POST'])
def push_to_recruitcrm():
    """Push generated summary to RecruitCRM candidate record"""
    app.logger.info("\n--- Endpoint Hit: /api/push-to-recruitcrm ---")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        html_summary = data.get('html_summary')

        if not candidate_slug or not html_summary:
            return jsonify({'error': 'Missing candidate slug or HTML summary'}), 400

        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {'candidate_summary': (None, html_summary)}

        response = requests.post(url, files=files, headers=get_recruitcrm_headers())

        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Summary pushed to RecruitCRM successfully'})
        else:
            app.logger.error(f"!!! ERROR: Failed to update RecruitCRM: {response.text}")
            return jsonify({'error': f'Failed to update RecruitCRM: {response.text}'}), 500

    except Exception as e:
        app.logger.error(f"!!! TOP-LEVEL EXCEPTION in push_to_recruitcrm: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-multiple-candidates', methods=['POST'])
def generate_multiple_candidates():
    """
    Generates content for multiple candidates.
    This function is designed to be called with a list of candidate slugs,
    not full URLs, to ensure we use the correct internal data fetching methods.
    """
    app.logger.info("\n--- Endpoint Hit: /api/generate-multiple-candidates ---")
    try:
        data = request.get_json()
        candidate_slugs = data.get('candidate_slugs', [])
        job_slug = data.get('job_slug')
        prompt_type = data.get('prompt_type', 'candidate-submission')
        client_name = data.get('client_name', '')
        preferred_candidate = data.get('preferred_candidate', '')
        additional_context = data.get('additional_context', '')

        if not candidate_slugs or not job_slug:
            return jsonify({'error': 'At least one candidate slug and a job slug are required'}), 400

        app.logger.info(f"Processing {len(candidate_slugs)} candidates for job {job_slug}")

        job_data = fetch_recruitcrm_job(job_slug)
        if not job_data:
            return jsonify({'error': "Failed to fetch job data"}), 404

        job_details = job_data.get('data', job_data)
        job_title = job_details.get('name', '')
        alpharun_job_id = None
        for field in job_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                alpharun_job_id = field.get('value')
                break

        # Fetch all candidates for the job at once to get the rich data
        all_job_candidates = fetch_recruitcrm_assigned_candidates(job_slug)

        # Create a dictionary for quick lookup
        candidate_map = {
            c.get('candidate', {}).get('slug'): c.get('candidate', {})
            for c in all_job_candidates
        }

        candidates_data = []
        failed_candidates = []
        resume_files = []

        for i, slug in enumerate(candidate_slugs):
            candidate_details = candidate_map.get(slug)
            if not candidate_details:
                app.logger.warning(f"Could not find candidate with slug {slug} in the assigned list.")
                failed_candidates.append(slug)
                continue

            gemini_resume_file = None
            resume_info = candidate_details.get('resume')
            if resume_info:
                gemini_resume_file = upload_resume_to_gemini(resume_info)
                if gemini_resume_file:
                    resume_files.append(gemini_resume_file)

            interview_data = None
            if alpharun_job_id:
                for field in candidate_details.get('custom_fields', []):
                    if field.get('field_name') == 'AI Interview ID' and field.get('value'):
                        interview_id = field.get('value').split('?')[0]
                        interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)
                        break

            candidates_data.append({
                'basic_data': {'data': candidate_details}, # Keep the nested 'data' structure
                'resume_file': gemini_resume_file,
                'interview_data': interview_data,
                'candidate_number': i + 1
            })

        if not candidates_data:
            return jsonify({'error': 'No valid candidate data could be retrieved'}), 400

        # Build the prompt
        formatted_candidates_data = ""
        for candidate_info in candidates_data:
            details = candidate_info['basic_data']['data']
            num = candidate_info['candidate_number']
            formatted_candidates_data += f"\n**CANDIDATE {num}: {details.get('first_name')} {details.get('last_name')}**\n"
            # Add more fields as needed for the prompt
            if candidate_info['resume_file']:
                formatted_candidates_data += f"Resume: Available for AI analysis\n"
            if candidate_info['interview_data']:
                formatted_candidates_data += f"Interview: Completed\n"

        prompt_kwargs = {
            'client_name': client_name,
            'job_url': f"https://app.recruitcrm.io/jobs/{job_slug}",
            'preferred_candidate': preferred_candidate,
            'additional_context': additional_context,
            'candidates_data': formatted_candidates_data,
            'job_data': job_details,
            'job_title': job_title,
        }
        full_prompt = build_full_prompt(prompt_type, "multiple", **prompt_kwargs)

        prompt_contents = [full_prompt]
        if resume_files:
            prompt_contents.extend(resume_files)

        response = model.generate_content(prompt_contents)
        cleaned_content = re.sub(r'^```html\n|```$', '', response.text, flags=re.MULTILINE)

        final_content = cleaned_content.replace('[HERE_LINK]', f'<a href="https://app.recruitcrm.io/jobs/{job_slug}">here</a>')

        return jsonify({
            'success': True,
            'generated_content': final_content,
        }), 200

    except Exception as e:
        app.logger.error(f"!!! EXCEPTION in generate_multiple_candidates: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/api/bulk-process-job', methods=['POST'])
def bulk_process_job():
    """
    Processes a job by fetching candidates at a specific stage, generating individual summaries,
    and optionally creating a multi-candidate email.
    """
    app.logger.info("\n--- Endpoint Hit: /api/bulk-process-job ---")
    data = request.get_json()

    job_url = data.get('job_url')
    single_prompt = data.get('single_candidate_prompt')
    multi_prompt = data.get('multi_candidate_prompt')
    generate_email = data.get('generate_email', False)
    auto_push = data.get('auto_push', False)
    status_id = data.get('status_id')

    if not job_url or not single_prompt:
        return jsonify({'error': 'Missing job_url or single_candidate_prompt'}), 400

    try:
        job_slug = job_url.split('/')[-1]
        job_data = fetch_recruitcrm_job(job_slug)
        if not job_data:
            return jsonify({'error': f"Could not fetch job data for slug: {job_slug}"}), 404

        job_details = job_data.get('data', job_data)
        alpharun_job_id = None
        for field in job_details.get('custom_fields', []):
            if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                alpharun_job_id = field.get('value')
                break

        candidates = fetch_recruitcrm_assigned_candidates(job_slug, status_id)
        if not candidates:
            return jsonify({'success': True, 'message': f"No candidates found."}), 200

        app.logger.info(f"Found {len(candidates)} candidates to process for job {job_slug}.")

        processed_summaries = {}
        failed_candidates = {}
        candidate_slugs_for_email = []

        for cand_info in candidates:
            full_candidate_data = cand_info.get('candidate', {})
            slug = full_candidate_data.get('slug')
            name = f"{full_candidate_data.get('first_name', '')} {full_candidate_data.get('last_name', '')}".strip()

            if not slug:
                continue

            app.logger.info(f"Processing candidate: {name} ({slug})")
            candidate_slugs_for_email.append(slug)

            try:
                gemini_resume_file = None
                resume_info = full_candidate_data.get('resume')
                if resume_info:
                    gemini_resume_file = upload_resume_to_gemini(resume_info)

                interview_data = None
                if alpharun_job_id:
                    for field in full_candidate_data.get('custom_fields', []):
                        if field.get('field_name') == 'AI Interview ID' and field.get('value'):
                            interview_id = field.get('value').split('?')[0]
                            interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)
                            break

                summary_input_data = {'data': full_candidate_data}
                summary = generate_html_summary(summary_input_data, job_data, interview_data, "", single_prompt, None, gemini_resume_file, model)

                if summary:
                    processed_summaries[name or slug] = summary
                    if auto_push:
                        push_to_recruitcrm_internal(slug, summary)
                else:
                    failed_candidates[name or slug] = "AI failed to generate summary."

            except Exception as e:
                app.logger.error(f"Exception processing candidate {slug}: {e}")
                failed_candidates[name or slug] = f"An unexpected error occurred: {e}"

        email_html = None
        if generate_email and multi_prompt and candidate_slugs_for_email:
            email_request_body = {
                "candidate_slugs": candidate_slugs_for_email,
                "job_slug": job_slug,
                "prompt_type": multi_prompt,
                "client_name": job_details.get('company', {}).get('name', 'Valued Client'),
            }
            # Use a test client to make an internal request to our corrected endpoint
            with app.test_request_context('/api/generate-multiple-candidates', method='POST', json=email_request_body):
                response = generate_multiple_candidates()
                if response.status_code == 200:
                    email_html = response.get_json().get('generated_content')

        return jsonify({
            'success': True,
            'job_title': job_details.get('name'),
            'candidates_found': len(candidates),
            'summaries_generated': len(processed_summaries),
            'summaries': processed_summaries,
            'pushes_attempted': len(processed_summaries) if auto_push else 0,
            'failures': len(failed_candidates),
            'failed_candidates': failed_candidates,
            'email_html': email_html
        }), 200

    except Exception as e:
        app.logger.error(f"!!! TOP-LEVEL EXCEPTION in bulk_process_job: {e}")
        return jsonify({'error': str(e)}), 500

def push_to_recruitcrm_internal(candidate_slug, html_summary):
    """Internal function to push summary, returns success status."""
    try:
        url = f"https://api.recruitcrm.io/v1/candidates/{candidate_slug}"
        files = {'candidate_summary': (None, html_summary)}
        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        if response.status_code == 200:
            logging.info(f"Successfully pushed summary for {candidate_slug}")
            return True
        else:
            logging.error(f"Failed to push summary for {candidate_slug}: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Exception in push_to_recruitcrm_internal for {candidate_slug}: {e}")
        return False

@app.route('/api/log-feedback', methods=['POST'])
def log_feedback():
    """Receives and logs user feedback on a generated summary to Firestore."""
    app.logger.info("\n--- Endpoint Hit: /api/log-feedback ---")
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
        app.logger.error(f"!!! EXCEPTION in log_feedback: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# ==============================================================================
# 3. MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)