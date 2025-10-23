# app.py

import os
import logging
import sys
import structlog
from flask import Flask, jsonify, request
import uuid

# Add the project's root directory to the Python path
# This MUST be at the top, before other local imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask_cors import CORS
from dotenv import load_dotenv
import google.genai as genai
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
         "http://localhost:3000",
         "http://localhost:5174"
         # Local development (Create React App)
     ],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True
     )

# --- Configure Logging ---
# CRITICAL: This MUST be configured BEFORE importing any modules that use structlog
logging.basicConfig(level=logging.INFO, format="%(message)s")

def rename_level_to_severity(logger, method_name, event_dict):
    """
    Log processor to rename the 'level' key to 'severity' and format it for
    Google Cloud Logging.
    """
    if "level" in event_dict:
        level = event_dict.pop("level")
        # Map standard log levels to Google Cloud Logging's severity levels
        severity_mapping = {
            "debug": "DEBUG",
            "info": "INFO",
            "warning": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL",
        }
        event_dict["severity"] = severity_mapping.get(level, "DEFAULT")
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        rename_level_to_severity,  # <-- Add this line
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

@app.before_request
def before_request():
    request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)

# --- Environment Variable Checks ---
# (These are used by helpers, but good to check at startup)
required_keys = ['RECRUITCRM_API_KEY', 'ALPHARUN_API_KEY', 'GOOGLE_API_KEY', 'FIREFLIES_API_KEY']
for key in required_keys:
    if not os.getenv(key):
        log.error("environment_variable_not_set", variable=key)

# --- Configure Google Gemini ---
try:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    client = genai.Client(
        api_key=GOOGLE_API_KEY
    )
    app.client = client  # Attach client to app context
    log.info("google_gemini.configured")
except Exception as e:
    log.error("google_gemini.configuration_failed", error=str(e))
    app.client = None

# --- Firestore Configuration ---
try:
    db = firestore.Client()
    app.db = db  # Attach db to app context
    log.info("firestore_client.initialized")
except Exception as e:
    log.error("firestore_client.initialization_failed", error=str(e))
    app.db = None


# ==============================================================================
# 2. BLUEPRINT REGISTRATION
# ==============================================================================
# Now structlog is configured, safe to import modules that use it
log.info("importing_blueprints")
try:
    log.info("Importing routes.single...")
    from routes.single import single_bp
    log.info("Successfully imported routes.single.")

    log.info("Importing routes.multi...")
    from routes.multi import multi_bp
    log.info("Successfully imported routes.multi.")

    log.info("Importing routes.bulk...")
    from routes.bulk import bulk_bp
    log.info("Successfully imported routes.bulk.")

    log.info("Importing routes.webhooks...")
    from routes.webhooks import webhooks_bp
    log.info("Successfully imported routes.webhooks.")

    log.info("blueprints_imported")

    log.info("registering_blueprints")
    app.register_blueprint(single_bp, url_prefix='/api')
    app.register_blueprint(multi_bp, url_prefix='/api')
    app.register_blueprint(bulk_bp, url_prefix='/api')
    app.register_blueprint(webhooks_bp, url_prefix='/api')
    log.info("blueprints_registered")

except Exception as e:
    log.error("An error occurred during blueprint import.", error=str(e), exc_info=True)
    # Exit here if an import fails, to make it clear.
    import sys
    sys.exit(1)


# ==============================================================================
# 3. CORE ROUTES
# ==============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint to confirm the server is running."""
    log.info("health_check.endpoint.hit")
    return jsonify({'status': 'healthy'}), 200


# ==============================================================================
# 4. MAIN EXECUTION BLOCK
# ==============================================================================

if __name__ == '__main__':
    log.info("flask_server.starting")
    app.run(debug=False, host='0.0.0.0', port=5000)