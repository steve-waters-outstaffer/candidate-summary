import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore

# Import helper functions from your new helpers.py file
from helpers import (
    fetch_recruitcrm_candidate, fetch_recruitcrm_job, fetch_alpharun_interview,
    upload_resume_to_gemini, generate_html_summary, generate_ai_response,
    extract_fireflies_transcript_id, fetch_fireflies_transcript,
    normalise_fireflies_transcript, get_slug_from_url
)
from config.prompts import build_full_prompt, get_available_prompts

# ==============================================================================
# 1. INITIALIZATION & CONFIGURATION
# ==============================================================================

load_dotenv()
app = Flask(__name__)

# This CORS configuration is correct. The warning is informational.
CORS(app,
     origins=[
         "https://candidate-summary-ai.web.app",
         "http://localhost:5173",
         "http://localhost:3000"
     ],
     methods=["GET", "POST", "OPTIONS"],
     headers=["Content-Type", "Authorization"],
     supports_credentials=True)

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    app.logger.error("!!! FATAL ERROR: GOOGLE_API_KEY environment variable is not set.")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    app.logger.info("LOG: Google Gemini configured successfully.")
except Exception as e:
    app.logger.error(f"!!! FATAL ERROR: Could not configure Google Gemini: {e}")

try:
    db = firestore.Client()
    app.logger.info("LOG: Firestore client initialized successfully.")
except Exception as e:
    app.logger.error(f"!!! FATAL ERROR: Could not initialize Firestore client: {e}")
    db = None

# ==============================================================================
# API ROUTES
# ==============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint."""
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/prompts', methods=['GET'])
def list_prompts():
    """Returns a list of available prompt configurations."""
    category = request.args.get('category', 'single')
    try:
        prompts = get_available_prompts(category)
        return jsonify(prompts), 200
    except Exception as e:
        app.logger.error(f"!!! EXCEPTION in list_prompts: {e}")
        return jsonify({'error': 'Could not retrieve prompt list'}), 500

# --- SINGLE CANDIDATE GENERATOR ROUTE ---
@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    """Endpoint for generating a summary for a single candidate."""
    app.logger.info("\n--- Endpoint Hit: /api/generate-summary ---")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        job_slug = data.get('job_slug')

        if not all([candidate_slug, job_slug]):
            return jsonify({'error': 'Missing required RecruitCRM fields'}), 400

        # Fetch all data
        candidate_data = fetch_recruitcrm_candidate(candidate_slug)
        job_data = fetch_recruitcrm_job(job_slug)

        if not all([candidate_data, job_data]):
            return jsonify({'error': 'Failed to fetch critical candidate or job data'}), 500

        # Resume handling
        gemini_resume_file = None
        if resume_info := candidate_data.get('data', {}).get('resume'):
            gemini_resume_file = upload_resume_to_gemini(resume_info)

        # Interview handling
        interview_data = None
        if job_alpharun_id := job_data.get('data', {}).get('custom_fields', [{}])[0].get('value'):
            for field in candidate_data.get('data', {}).get('custom_fields', []):
                if field.get('field_name') == 'AI Interview ID' and field.get('value'):
                    interview_id = field.get('value').split('?')[0]
                    interview_data = fetch_alpharun_interview(job_alpharun_id, interview_id)
                    break

        # Fireflies handling
        fireflies_data = None
        if fireflies_url := data.get('fireflies_url'):
            if transcript_id := extract_fireflies_transcript_id(fireflies_url):
                raw_transcript = fetch_fireflies_transcript(transcript_id)
                fireflies_data = normalise_fireflies_transcript(raw_transcript)

        # Generate summary
        html_summary = generate_html_summary(
            candidate_data=candidate_data,
            job_data=job_data,
            interview_data=interview_data,
            additional_context=data.get('additional_context', ''),
            prompt_type=data.get('prompt_type', 'recruitment.detailed'),
            fireflies_data=fireflies_data,
            gemini_resume_file=gemini_resume_file
        )

        if html_summary:
            return jsonify({'success': True, 'html_summary': html_summary})
        else:
            return jsonify({'error': 'Failed to generate summary from AI model'}), 500

    except Exception as e:
        app.logger.error(f"!!! TOP-LEVEL EXCEPTION in generate_summary: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# --- MULTIPLE CANDIDATE GENERATOR ROUTE ---
@app.route('/api/generate-multiple-candidates', methods=['POST'])
def generate_multiple_candidates():
    """Endpoint for generating content for multiple candidates."""
    app.logger.info("\n--- Endpoint Hit: /api/generate-multiple-candidates ---")
    try:
        data = request.get_json()
        candidate_urls = data.get('candidate_urls', [])
        job_url = data.get('job_url')

        if not candidate_urls:
            return jsonify({'error': 'At least one candidate URL is required'}), 400

        job_data, job_alpharun_id = None, None
        if job_url:
            job_slug = get_slug_from_url(job_url)
            job_data = fetch_recruitcrm_job(job_slug)
            if job_data:
                for field in job_data.get('data', {}).get('custom_fields', []):
                    if field.get('field_name') == 'AI Job ID':
                        job_alpharun_id = field.get('value')
                        break

        all_candidates_processed_data = []
        gemini_files = []
        failed_urls = []

        for url in candidate_urls:
            slug = get_slug_from_url(url)
            candidate_data = fetch_recruitcrm_candidate(slug)
            if not candidate_data:
                failed_urls.append(url)
                continue

            candidate_details = candidate_data.get('data', {})

            # 1. Fetch Resume
            resume_file = None
            if resume_info := candidate_details.get('resume'):
                if uploaded_file := upload_resume_to_gemini(resume_info):
                    resume_file = uploaded_file
                    gemini_files.append(uploaded_file)

            # 2. Fetch Interview
            interview_id = None
            for field in candidate_details.get('custom_fields', []):
                if field.get('field_name') == 'AI Interview ID' and field.get('value'):
                    interview_id = field.get('value').split('?')[0]
                    break

            interview_data = fetch_alpharun_interview(job_alpharun_id, interview_id)

            all_candidates_processed_data.append({
                "candidate_data": candidate_data,
                "resume_file_name": resume_file.display_name if resume_file else None,
                "interview_data": interview_data
            })

        if not all_candidates_processed_data:
            return jsonify({'error': 'No valid candidate data could be retrieved'}), 400

        prompt_text = build_full_prompt(
            prompt_type=data.get('prompt_type', 'candidate-submission'),
            category="multiple",
            client_name=data.get('client_name', ''),
            job_data=job_data,
            candidates_data=all_candidates_processed_data,
            preferred_candidate=data.get('preferred_candidate', ''),
            additional_context=data.get('additional_context', '')
        )

        ai_response = generate_ai_response(prompt_text, files=gemini_files)

        if not ai_response:
            return jsonify({'error': 'Failed to generate AI content'}), 500

        final_content = ai_response
        if job_url:
            final_content = ai_response.replace('[HERE_LINK]', f'<a href="{job_url}">here</a>')

        return jsonify({
            'success': True,
            'generated_content': final_content,
        }), 200

    except Exception as e:
        app.logger.error(f"!!! TOP-LEVEL EXCEPTION in generate_multiple_candidates: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# --- FEEDBACK ROUTE ---
@app.route('/api/log-feedback', methods=['POST'])
def log_feedback():
    """Receives and logs user feedback to Firestore."""
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
        db.collection('feedback').add(feedback_data)
        return jsonify({'success': True, 'message': 'Feedback logged successfully'}), 200
    except Exception as e:
        app.logger.error(f"!!! EXCEPTION in log_feedback: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# ==============================================================================
# 4. MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))