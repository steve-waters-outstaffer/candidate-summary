import os
import requests
import logging
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore
from config.prompts import build_full_prompt

# ==============================================================================
# 1. INITIALIZATION & CONFIGURATION
# ==============================================================================

# Load environment variables from a .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# --- MODIFIED: More explicit CORS configuration to handle preflight requests ---
CORS(app,
     origins=[
         "https://candidate-summary-ai.web.app",  # Deployed frontend
         "http://localhost:5173",                 # Local development (Vite)
         "http://localhost:3000"                  # Local development (Create React App)
     ],
     methods=["GET", "POST", "OPTIONS"],
     headers=["Content-Type", "Authorization"],
     supports_credentials=True
     )


# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)

# --- API Configuration ---
RECRUITCRM_BASE_URL = "https://api.recruitcrm.io/v1"
ALPHARUN_BASE_URL = "https://api.alpharun.com/api/v1"

# --- Environment Variable Checks ---
RECRUITCRM_API_KEY = os.getenv('RECRUITCRM_API_KEY')
ALPHARUN_API_KEY = os.getenv('ALPHARUN_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not RECRUITCRM_API_KEY:
    app.logger.error("!!! FATAL ERROR: RECRUITCRM_API_KEY environment variable is not set.")
if not ALPHARUN_API_KEY:
    app.logger.error("!!! FATAL ERROR: ALPHARUN_API_KEY environment variable is not set.")
if not GOOGLE_API_KEY:
    app.logger.error("!!! FATAL ERROR: GOOGLE_API_KEY environment variable is not set.")

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
# 2. EXTERNAL API HELPER FUNCTIONS
# ==============================================================================

def get_recruitcrm_headers():
    """Returns the authorization headers for RecruitCRM."""
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {RECRUITCRM_API_KEY}"
    }

def get_alpharun_headers():
    """Returns the authorization headers for AlphaRun."""
    return {
        "Authorization": f"Bearer {ALPHARUN_API_KEY}"
    }

def fetch_recruitcrm_candidate(slug):
    """Fetches a single candidate record from RecruitCRM."""
    url = f"{RECRUITCRM_BASE_URL}/candidates/{slug}"
    app.logger.info(f"LOG: Fetching candidate from {url}")
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        app.logger.info(f"LOG: RecruitCRM candidate API status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"!!! ERROR: RecruitCRM candidate API failed. Body: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        app.logger.error(f"!!! EXCEPTION during candidate fetch: {e}")
        return None

def fetch_recruitcrm_job(slug):
    """Fetches a single job record from RecruitCRM."""
    url = f"{RECRUITCRM_BASE_URL}/jobs/{slug}"
    app.logger.info(f"LOG: Fetching job from {url}")
    try:
        response = requests.get(url, headers=get_recruitcrm_headers())
        app.logger.info(f"LOG: RecruitCRM job API status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"!!! ERROR: RecruitCRM job API failed. Body: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        app.logger.error(f"!!! EXCEPTION during job fetch: {e}")
        return None

def fetch_alpharun_interview(job_opening_id, interview_id):
    """Fetches interview data from AlphaRun using the job opening ID."""
    url = f"{ALPHARUN_BASE_URL}/job-openings/{job_opening_id}/interviews/{interview_id}"
    app.logger.info(f"LOG: Fetching interview from {url}")
    try:
        response = requests.get(url, headers=get_alpharun_headers())
        app.logger.info(f"LOG: AlphaRun interview API status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"!!! ERROR: AlphaRun interview API failed. Body: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        app.logger.error(f"!!! EXCEPTION during interview fetch: {e}")
        return None

def generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type):
    """Generate HTML summary using Google Gemini and clean the response."""
    app.logger.info(f"LOG: Generating HTML summary with Gemini using prompt type: {prompt_type}")

    # Build the full prompt using the function from prompts.py
    prompt = build_full_prompt(
        prompt_type=prompt_type,
        candidate_data=candidate_data,
        job_data=job_data,
        interview_data=interview_data,
        additional_context=additional_context
    )

    try:
        response = model.generate_content(prompt)
        raw_html = response.text

        # Clean the response to remove markdown code fences
        app.logger.info("LOG: Cleaning Gemini response.")
        cleaned_html = raw_html.strip()
        if cleaned_html.startswith("```html"):
            cleaned_html = cleaned_html[7:]
        if cleaned_html.endswith("```"):
            cleaned_html = cleaned_html[:-3]

        return cleaned_html.strip()

    except Exception as e:
        app.logger.error(f"!!! EXCEPTION during Gemini summary generation: {e}")
        return None

# ==============================================================================
# 3. FLASK API ROUTES
# ==============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint to confirm the server is running."""
    app.logger.info("LOG: Health check endpoint was hit.")
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/test-candidate', methods=['POST'])
def test_candidate():
    """Tests the connection to the RecruitCRM candidate API and extracts the AI Interview ID."""
    app.logger.info("\n--- Endpoint Hit: /api/test-candidate ---")
    data = request.get_json()
    if not data or 'candidate_slug' not in data:
        return jsonify({'error': 'Missing candidate_slug in request body'}), 400
    slug = data['candidate_slug']
    app.logger.info(f"LOG: Testing with candidate slug: {slug}")

    response_data = fetch_recruitcrm_candidate(slug)
    if response_data:
        candidate_details = response_data.get('data', response_data)
        interview_id = None

        custom_fields = candidate_details.get('custom_fields', [])
        if isinstance(custom_fields, list):
            for field in custom_fields:
                if isinstance(field, dict) and field.get('field_name') == 'AI Interview ID':
                    interview_id = field.get('value')
                    app.logger.info(f"LOG: Found AI Interview ID: {interview_id}")
                    break

        return jsonify({
            'success': True,
            'message': 'Candidate confirmed',
            'candidate_name': f"{candidate_details.get('first_name', '')} {candidate_details.get('last_name', '')}".strip(),
            'interview_id': interview_id
        })
    else:
        return jsonify({'error': 'Failed to fetch candidate data'}), 404

@app.route('/api/test-job', methods=['POST'])
def test_job():
    """Tests the connection to the RecruitCRM job API and extracts the AI Job ID."""
    app.logger.info("\n--- Endpoint Hit: /api/test-job ---")
    data = request.get_json()
    if not data or 'job_slug' not in data:
        return jsonify({'error': 'Missing job_slug in request body'}), 400
    slug = data['job_slug']
    app.logger.info(f"LOG: Testing with job slug: {slug}")

    response_data = fetch_recruitcrm_job(slug)
    if response_data:
        job_details = response_data.get('data', response_data)
        alpharun_job_id = None

        custom_fields = job_details.get('custom_fields', [])
        if isinstance(custom_fields, list):
            for field in custom_fields:
                if isinstance(field, dict) and field.get('field_name') == 'AI Job ID':
                    alpharun_job_id = field.get('value')
                    app.logger.info(f"LOG: Found AI Job ID: {alpharun_job_id}")
                    break

        return jsonify({
            'success': True,
            'message': 'Job confirmed',
            'job_name': job_details.get('name', 'Unknown Job'),
            'alpharun_job_id': alpharun_job_id
        })
    else:
        return jsonify({'error': 'Failed to fetch job data'}), 404

@app.route('/api/test-interview', methods=['POST'])
def test_interview():
    """Tests the connection to the AlphaRun interview API."""
    app.logger.info("\n--- Endpoint Hit: /api/test-interview ---")
    data = request.get_json()
    if not data or 'interview_id' not in data or 'alpharun_job_id' not in data:
        return jsonify({'error': 'Missing interview_id or alpharun_job_id in request body'}), 400
    interview_id = data['interview_id']
    job_opening_id = data['alpharun_job_id']
    app.logger.info(f"LOG: Testing with AlphaRun Job ID: {job_opening_id} and Interview ID: {interview_id}")
    interview_data = fetch_alpharun_interview(job_opening_id, interview_id)
    if interview_data:
        contact = interview_data.get('data', {}).get('interview', {}).get('contact', {})
        return jsonify({
            'success': True, 'message': 'Interview confirmed',
            'candidate_name': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        })
    else:
        return jsonify({'error': 'Failed to fetch interview data'}), 404

@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    """Generate candidate summary from provided slugs and interview ID"""
    app.logger.info("\n--- Endpoint Hit: /api/generate-summary ---")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        job_slug = data.get('job_slug')
        alpharun_job_id = data.get('alpharun_job_id')
        interview_id = data.get('interview_id')
        additional_context = data.get('additional_context', '')
        # Get the prompt_type from the request, default if not provided
        prompt_type = data.get('prompt_type', 'recruitment.detailed')

        if not all([candidate_slug, job_slug, interview_id, alpharun_job_id]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Fetch data from APIs
        candidate_data = fetch_recruitcrm_candidate(candidate_slug)
        job_data = fetch_recruitcrm_job(job_slug)
        interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)

        if not all([candidate_data, job_data, interview_data]):
            missing = [name for name, data in [("candidate", candidate_data), ("job", job_data), ("interview", interview_data)] if not data]
            app.logger.error(f"!!! ERROR: Missing data for: {', '.join(missing)}")
            return jsonify({'error': f'Failed to fetch data from: {", ".join(missing)}', 'missing_apis': missing}), 500

        # Generate HTML summary using Gemini, passing the prompt_type
        html_summary = generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type)

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

        url = f"{RECRUITCRM_BASE_URL}/candidates/{candidate_slug}"
        # RecruitCRM uses form-data for this specific update, so we use 'files'
        files = {'candidate_summary': (None, html_summary)}

        app.logger.info(f"LOG: Pushing summary to {url}")
        response = requests.post(url, files=files, headers=get_recruitcrm_headers())
        app.logger.info(f"LOG: RecruitCRM push response status: {response.status_code}")

        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Summary pushed to RecruitCRM successfully'})
        else:
            app.logger.error(f"!!! ERROR: Failed to update RecruitCRM: {response.text}")
            return jsonify({'error': f'Failed to update RecruitCRM: {response.text}'}), 500

    except Exception as e:
        app.logger.error(f"!!! TOP-LEVEL EXCEPTION in push_to_recruitcrm: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/log-feedback', methods=['POST'])
def log_feedback():
    """Receives and logs user feedback on a generated summary to Firestore."""
    app.logger.info("\n--- Endpoint Hit: /api/log-feedback ---")

    if not db:
        app.logger.error("!!! ERROR: Firestore client not initialized. Cannot log feedback.")
        return jsonify({'error': 'Firestore is not configured on the server'}), 500

    try:
        data = request.get_json()

        # Prepare the data for Firestore
        feedback_data = {
            'rating': data.get('rating'),
            'comments': data.get('comments', ''),
            'prompt_type': data.get('prompt_type'),
            'generated_summary_html': data.get('generated_summary_html'),
            'candidate_slug': data.get('candidate_slug'),
            'job_slug': data.get('job_slug'),
            'timestamp': datetime.datetime.utcnow()
        }

        # Add a new doc with a generated id to the 'feedback' collection
        feedback_ref = db.collection('feedback').document()
        feedback_ref.set(feedback_data)

        app.logger.info(f"LOG: Feedback logged successfully to Firestore with ID: {feedback_ref.id}")
        return jsonify({'success': True, 'message': 'Feedback logged successfully'}), 200

    except Exception as e:
        app.logger.error(f"!!! EXCEPTION in log_feedback: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# ==============================================================================
# 4. MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
