import os
import re
import requests
import logging
import datetime
import io
import mimetypes  # <-- New import
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore
from config.prompts import build_full_prompt
from urllib.parse import urlparse

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
FIREFLIES_GRAPHQL_URL = "https://api.fireflies.ai/graphql"

# --- Environment Variable Checks ---
RECRUITCRM_API_KEY = os.getenv('RECRUITCRM_API_KEY')
ALPHARUN_API_KEY = os.getenv('ALPHARUN_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
FIREFLIES_API_KEY = os.getenv('FIREFLIES_API_KEY') # Now read from server environment


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

# --- Fireflies.ai Helper Functions ---

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

def extract_fireflies_transcript_id(s: str) -> str | None:
    """Parses a string to find a Fireflies transcript ID."""
    s = s.strip()
    if s.startswith("http://") or s.startswith("https://"):
        try:
            path_segment = urlparse(s).path.rsplit("/", 1)[-1]
            parts = path_segment.split("::")
            if len(parts) == 2 and ULID_PATTERN.fullmatch(parts[1]):
                return parts[1]
        except (IndexError, ValueError):
            return None
    if ULID_PATTERN.fullmatch(s):
        return s
    return None

def fetch_fireflies_transcript(transcript_id: str) -> dict:
    """Fetches a transcript from the Fireflies GraphQL API using the server's API key."""
    headers = {
        "Authorization": f"Bearer {FIREFLIES_API_KEY}",
        "Content-Type": "application/json",
    }
    query = """
    query Transcript($id: String!) {
      transcript(id: $id) {
        id title date duration transcript_url
        speakers { id name }
        sentences { index speaker_name start_time end_time text }
      }
    }
    """
    variables = {"id": transcript_id}
    app.logger.info(f"LOG: Fetching Fireflies transcript ID: {transcript_id}")
    try:
        resp = requests.post(
            FIREFLIES_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            app.logger.error(f"!!! ERROR: Fireflies GraphQL error: {payload['errors']}")
            return None
        return payload.get("data", {}).get("transcript")
    except requests.exceptions.RequestException as e:
        app.logger.error(f"!!! EXCEPTION during Fireflies fetch: {e}")
        return None

def normalise_fireflies_transcript(tr: dict) -> dict:
    """Produces a compact, LLM-ready JSON from the raw transcript data."""
    app.logger.info("LOG: Normalising Fireflies transcript for LLM.")
    speakers = [s.get("name") for s in (tr.get("speakers") or []) if s and s.get("name")]
    lines = []
    for s in (tr.get("sentences") or []):
        speaker = s.get("speaker_name") or "Unknown"
        text = s.get("text") or ""
        lines.append(f"{speaker}: {text}".strip())

    return {
        "metadata": {
            "title": tr.get("title"),
            "url": tr.get("transcript_url"),
            "speakers": speakers,
        },
        "content": "\n".join(lines),
    }

# --- END: Fireflies.ai Helper Functions ---


# --- CORRECTED HELPER FUNCTION FOR RESUME HANDLING ---
def upload_resume_to_gemini(resume_data: dict) -> dict | None:
    """
    Downloads a resume from RecruitCRM and uploads it to the Gemini File API.
    Returns the file object from the Gemini API if successful.
    """
    if not resume_data or 'file_link' not in resume_data or 'filename' not in resume_data:
        app.logger.info("LOG: No valid resume data provided.")
        return None

    file_link = resume_data['file_link']
    filename = resume_data['filename']
    app.logger.info(f"LOG: Attempting to process resume: {filename}")

    # --- FIX: Determine the mime type from the filename ---
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        # Provide a default or handle the case where the type is unknown
        mime_type = 'application/octet-stream' # A generic binary type
        app.logger.warning(f"Could not determine mime type for {filename}, using default: {mime_type}")


    try:
        # 1. Download the resume file from RecruitCRM
        response = requests.get(file_link, timeout=30)
        response.raise_for_status()
        resume_bytes = response.content
        app.logger.info(f"LOG: Successfully downloaded {filename} from RecruitCRM.")

        # 2. Upload the file content to the Gemini File API with the mime_type
        gemini_file = genai.upload_file(
            path=io.BytesIO(resume_bytes),
            display_name=filename,
            mime_type=mime_type  # <-- This is the required fix
        )
        app.logger.info(f"LOG: Successfully uploaded resume to Gemini. URI: {gemini_file.uri}")

        return gemini_file

    except requests.exceptions.RequestException as e:
        app.logger.error(f"!!! EXCEPTION during resume download: {e}")
        return None
    except Exception as e:
        app.logger.error(f"!!! EXCEPTION during resume upload to Gemini: {e}")
        return None
# --- END OF CORRECTED HELPER FUNCTION ---


def generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data=None, gemini_resume_file=None):
    """Generate HTML summary using Google Gemini and clean the response."""
    app.logger.info(f"LOG: Generating HTML summary with Gemini using prompt type: {prompt_type}")

    prompt_text = build_full_prompt(
        prompt_type=prompt_type,
        candidate_data=candidate_data,
        job_data=job_data,
        interview_data=interview_data,
        additional_context=additional_context,
        fireflies_data=fireflies_data
    )

    prompt_contents = [prompt_text]

    if gemini_resume_file:
        prompt_contents.append(gemini_resume_file)
        app.logger.info("LOG: Appending resume file to Gemini prompt.")

    try:
        response = model.generate_content(prompt_contents)
        raw_html = response.text
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
                interview_id = field.get('value')
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
    interview_id = data.get('interview_id')
    job_opening_id = data.get('alpharun_job_id')
    if not interview_id or not job_opening_id:
        return jsonify({'error': 'Missing interview_id or alpharun_job_id'}), 400

    interview_data = fetch_alpharun_interview(job_opening_id, interview_id)
    if interview_data:
        contact = interview_data.get('data', {}).get('interview', {}).get('contact', {})
        return jsonify({
            'success': True, 'message': 'Interview confirmed',
            'candidate_name': f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        })
    return jsonify({'error': 'Failed to fetch interview data'}), 404

# --- NEW: Fireflies.ai Test Endpoint ---
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


@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    """Generate candidate summary, optionally including Fireflies data."""
    app.logger.info("\n--- Endpoint Hit: /api/generate-summary ---")
    try:
        data = request.get_json()
        candidate_slug = data.get('candidate_slug')
        job_slug = data.get('job_slug')
        alpharun_job_id = data.get('alpharun_job_id')
        interview_id = data.get('interview_id')
        fireflies_url = data.get('fireflies_url') # Optional
        additional_context = data.get('additional_context', '')
        prompt_type = data.get('prompt_type', 'recruitment.detailed')

        if not all([candidate_slug, job_slug, interview_id, alpharun_job_id]):
            return jsonify({'error': 'Missing required RecruitCRM/AlphaRun fields'}), 400

        candidate_data = fetch_recruitcrm_candidate(candidate_slug)
        job_data = fetch_recruitcrm_job(job_slug)
        interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)

        # --- CORRECTED: Resume Handling Logic ---
        gemini_resume_file = None
        if candidate_data:
            # Safely access the nested 'data' object
            candidate_details = candidate_data.get('data', candidate_data)
            resume_info = candidate_details.get('resume')
            if resume_info:
                # This function will handle download and upload, returning None on failure
                gemini_resume_file = upload_resume_to_gemini(resume_info)
            else:
                app.logger.info("LOG: No resume object found in candidate data.")

        fireflies_data = None
        if fireflies_url:
            app.logger.info("LOG: Fireflies URL provided, fetching transcript...")
            transcript_id = extract_fireflies_transcript_id(fireflies_url)
            if transcript_id:
                raw_transcript = fetch_fireflies_transcript(transcript_id)
                if raw_transcript:
                    fireflies_data = normalise_fireflies_transcript(raw_transcript)
                else:
                    app.logger.warning("!!! WARNING: Failed to fetch Fireflies data, proceeding without it.")
            else:
                app.logger.warning("!!! WARNING: Invalid Fireflies URL, proceeding without it.")


        if not all([candidate_data, job_data, interview_data]):
            missing = [name for name, d in [("candidate", candidate_data), ("job", job_data), ("interview", interview_data)] if not d]
            return jsonify({'error': f'Failed to fetch data from: {", ".join(missing)}'}), 500

        html_summary = generate_html_summary(candidate_data, job_data, interview_data, additional_context, prompt_type, fireflies_data, gemini_resume_file)

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
# 4. MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)