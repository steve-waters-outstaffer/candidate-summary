# app.py

import os
import logging
import sys

# Add the project's root directory to the Python path
# This MUST be at the top, before other local imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore

# Load environment variables from a .env file
load_dotenv()

# ==============================================================================
# 1. INITIALIZATION & CONFIGURATION
# ==============================================================================

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
# (These are used by helpers, but good to check at startup)
required_keys = ['RECRUITCRM_API_KEY', 'ALPHARUN_API_KEY', 'GOOGLE_API_KEY', 'FIREFLIES_API_KEY']
for key in required_keys:
    if not os.getenv(key):
        app.logger.error(f"!!! FATAL ERROR: {key} environment variable is not set.")

# --- Configure Google Gemini ---
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    app.model = model  # Attach model to app context
    app.logger.info("LOG: Google Gemini configured successfully.")
except Exception as e:
    app.logger.error(f"!!! FATAL ERROR: Could not configure Google Gemini: {e}")
    app.model = None

# --- Firestore Configuration ---
try:
    db = firestore.Client()
    app.db = db  # Attach db to app context
    app.logger.info("LOG: Firestore client initialized successfully.")
except Exception as e:
    app.logger.error(f"!!! FATAL ERROR: Could not initialize Firestore client: {e}")
    app.db = None


# ==============================================================================
# 2. BLUEPRINT REGISTRATION
# ==============================================================================
from routes.single import single_bp
from routes.multi import multi_bp
from routes.bulk import bulk_bp

app.register_blueprint(single_bp, url_prefix='/api')
app.register_blueprint(multi_bp, url_prefix='/api')
app.register_blueprint(bulk_bp, url_prefix='/api')


# ==============================================================================
# 3. CORE ROUTES
# ==============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint to confirm the server is running."""
    app.logger.info("LOG: Health check endpoint was hit.")
    return jsonify({'status': 'healthy'}), 200


# ==============================================================================
# 4. MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)