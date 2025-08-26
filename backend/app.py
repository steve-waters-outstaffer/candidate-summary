import os
import re
import requests
import logging
import datetime
import io
import mimetypes  # <-- New import
from file_converter import convert_to_supported_format, UnsupportedFileTypeError
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore
from config.prompts import build_full_prompt, get_available_prompts
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
# --- UPDATED HELPER FUNCTION FOR RESUME HANDLING ---
def upload_resume_to_gemini(resume_data: dict) -> dict | None:
    """
    Downloads a resume, converts it to a supported format if necessary,
    and uploads it to the Gemini File API.
    Returns the file object from the Gemini API if successful.
    """
    if not resume_data or 'file_link' not in resume_data or 'filename' not in resume_data:
        app.logger.info("LOG: No valid resume data provided.")
        return None

    file_link = resume_data['file_link']
    filename = resume_data['filename']
    app.logger.info(f"LOG: Attempting to process resume: {filename}")

    try:
        # 1. Download the resume file from RecruitCRM
        response = requests.get(file_link, timeout=30)
        response.raise_for_status()
        resume_bytes = response.content
        app.logger.info(f"LOG: Successfully downloaded {filename} from RecruitCRM.")

        # 2. Convert the file to a supported format (e.g., text/plain) if needed
        try:
            converted_bytes, supported_mime_type = convert_to_supported_format(
                file_bytes=resume_bytes,
                original_filename=filename
            )
            app.logger.info(f"LOG: File '{filename}' processed for upload with MIME type '{supported_mime_type}'.")
        except UnsupportedFileTypeError as e:
            # Log a warning but don't crash the whole process.
            # The summary generation will proceed without the resume.
            app.logger.warning(f"!!! WARNING: Could not process resume. {e}")
            return None

        # 3. Upload the processed file content to the Gemini File API
        gemini_file = genai.upload_file(
            path=io.BytesIO(converted_bytes),
            display_name=filename,
            mime_type=supported_mime_type # <-- Use the new supported mime type
        )
        app.logger.info(f"LOG: Successfully uploaded resume to Gemini. URI: {gemini_file.uri}")

        return gemini_file

    except requests.exceptions.RequestException as e:
        app.logger.error(f"!!! EXCEPTION during resume download: {e}")
        return None
    except Exception as e:
        # This will catch errors from the Gemini API upload itself
        app.logger.error(f"!!! EXCEPTION during resume upload to Gemini: {e}")
        return None


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

    # Clean interview ID by removing URL parameters
    interview_id = raw_interview_id.split('?')[0]

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

# In backend/app.py

@app.route('/api/test-resume', methods=['POST'])
def test_resume():
    """Checks for the presence of a resume in the candidate data."""
    app.logger.info("\n--- Endpoint Hit: /api/test-resume ---")
    data = request.get_json()
    candidate_slug = data.get('candidate_slug')

    if not candidate_slug:
        return jsonify({'error': 'Missing candidate_slug'}), 400

    # We fetch the full candidate record just like the main function does
    candidate_data = fetch_recruitcrm_candidate(candidate_slug)

    if candidate_data:
        candidate_details = candidate_data.get('data', candidate_data)
        resume_info = candidate_details.get('resume')

        if resume_info and resume_info.get('filename'):
            return jsonify({
                'success': True,
                'message': 'Resume Found',
                'resume_name': resume_info.get('filename')
            })
        else:
            # It's not an error if there's no resume, just a different status
            return jsonify({
                'success': False, # Use success: false to indicate 'not found'
                'message': 'No resume on file for this candidate.'
            })

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
        fireflies_url = data.get('fireflies_url')  # Optional
        additional_context = data.get('additional_context', '')
        prompt_type = data.get('prompt_type', 'recruitment.detailed')

        # Clean interview ID by removing URL parameters
        interview_id = None
        if raw_interview_id:
            interview_id = raw_interview_id.split('?')[0]

        if not all([candidate_slug, job_slug]):
            return jsonify({'error': 'Missing required RecruitCRM fields'}), 400

        candidate_data = fetch_recruitcrm_candidate(candidate_slug)
        job_data = fetch_recruitcrm_job(job_slug)

        interview_data = None
        if alpharun_job_id and interview_id:
            interview_data = fetch_alpharun_interview(alpharun_job_id, interview_id)
            if not interview_data:
                app.logger.warning("!!! WARNING: Failed to fetch interview data, proceeding without it.")
        else:
            app.logger.info("LOG: No interview ID or AlphaRun job ID provided, proceeding without interview data.")

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

        if not all([candidate_data, job_data]):
            missing = [name for name, d in [("candidate", candidate_data), ("job", job_data)] if not d]
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

@app.route('/api/generate-multiple-candidates', methods=['POST'])
def generate_multiple_candidates():
    """Generates content for multiple candidates using multiple-candidates-prompts."""
    app.logger.info("\n--- Endpoint Hit: /api/generate-multiple-candidates ---")
    
    try:
        data = request.get_json()
        
        # Extract request data
        candidate_urls = data.get('candidate_urls', [])
        prompt_type = data.get('prompt_type', 'candidate-submission')
        client_name = data.get('client_name', '')
        job_url = data.get('job_url', '')
        preferred_candidate = data.get('preferred_candidate', '')
        additional_context = data.get('additional_context', '')
        
        # Validate input
        if not candidate_urls or len(candidate_urls) == 0:
            return jsonify({'error': 'At least one candidate URL is required'}), 400
        
        if len(candidate_urls) > 10:  # Safety limit
            return jsonify({'error': 'Maximum 10 candidates allowed'}), 400
        
        app.logger.info(f"Processing {len(candidate_urls)} candidates with prompt type: {prompt_type}")
        
        # Fetch job description if job_url provided
        job_data = None
        if job_url:
            try:
                app.logger.info(f"Fetching job description from: {job_url}")
                job_slug = job_url.split('/')[-1] if '/' in job_url else job_url
                job_response = fetch_recruitcrm_job(job_slug)
                if job_response:
                    job_data = job_response
                    app.logger.info("Successfully fetched job description")
                else:
                    app.logger.warning("Failed to fetch job description")
            except Exception as e:
                app.logger.error(f"Error fetching job description: {e}")
        
        # Process each candidate sequentially
        candidates_data = []
        failed_candidates = []
        
        for i, url in enumerate(candidate_urls):
            try:
                app.logger.info(f"Fetching candidate {i+1}/{len(candidate_urls)}: {url}")
                
                # Extract slug from URL (reuse existing logic)
                slug = url.split('/')[-1] if '/' in url else url
                
                # Fetch candidate data
                candidate_data = fetch_recruitcrm_candidate(slug)
                if candidate_data:
                    candidates_data.append(candidate_data)
                    app.logger.info(f"Successfully fetched candidate {i+1}")
                else:
                    failed_candidates.append(url)
                    app.logger.warning(f"Failed to fetch candidate {i+1}: {url}")
                    
            except Exception as e:
                app.logger.error(f"Error processing candidate {i+1}: {e}")
                failed_candidates.append(url)
        
        if not candidates_data:
            return jsonify({'error': 'No valid candidate data could be retrieved'}), 400
        
        # Prepare data for prompt generation
        formatted_candidates_data = ""
        for i, candidate in enumerate(candidates_data):
            candidate_details = candidate.get('data', candidate)
            formatted_candidates_data += f"\n**CANDIDATE {i+1}:**\n"
            formatted_candidates_data += f"Name: {candidate_details.get('first_name', '')} {candidate_details.get('last_name', '')}\n"
            formatted_candidates_data += f"Email: {candidate_details.get('email', '')}\n"
            formatted_candidates_data += f"Phone: {candidate_details.get('mobile_phone', '')}\n"
            
            # Add custom fields
            for field in candidate_details.get('custom_fields', []):
                if isinstance(field, dict) and field.get('value'):
                    formatted_candidates_data += f"{field.get('field_name', 'Unknown')}: {field.get('value')}\n"
            
            formatted_candidates_data += "\n"
        
        # Format job data if available
        formatted_job_data = ""
        if job_data:
            job_details = job_data.get('data', job_data)
            formatted_job_data = f"Job Title: {job_details.get('job_name', '')}\n"
            formatted_job_data += f"Company: {job_details.get('company_name', '')}\n"
            formatted_job_data += f"Location: {job_details.get('job_location', '')}\n"
            formatted_job_data += f"Description: {job_details.get('job_description', '')}\n"
            
            # Add custom fields
            for field in job_details.get('custom_fields', []):
                if isinstance(field, dict) and field.get('value'):
                    formatted_job_data += f"{field.get('field_name', 'Unknown')}: {field.get('value')}\n"

        # Build prompt using multiple-candidates-prompts
        prompt_kwargs = {
            'client_name': client_name,
            'job_url': job_url,
            'preferred_candidate': preferred_candidate,
            'additional_context': additional_context,
            'candidates_data': formatted_candidates_data,
            'job_data': formatted_job_data
        }
        
        full_prompt = build_full_prompt(prompt_type, "multiple", **prompt_kwargs)
        
        # Generate content with AI
        app.logger.info("Generating AI content for multiple candidates...")
        ai_response = generate_ai_response(full_prompt)
        
        if not ai_response:
            return jsonify({'error': 'Failed to generate AI content'}), 500
        
        # Replace placeholder links if job_url provided
        final_content = ai_response
        if job_url:
            final_content = ai_response.replace('[HERE_LINK]', f'<a href="{job_url}">here</a>')
        
        app.logger.info("Multiple candidates content generated successfully")
        
        response = {
            'success': True,
            'generated_content': final_content,
            'candidates_processed': len(candidates_data),
            'candidates_failed': len(failed_candidates),
            'failed_urls': failed_candidates
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        app.logger.error(f"!!! EXCEPTION in generate_multiple_candidates: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

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