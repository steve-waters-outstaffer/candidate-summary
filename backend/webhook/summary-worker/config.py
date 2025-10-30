# config.py
# Holds static configuration, constants, and database client.

import os
from google.cloud import firestore

# Environment variables
FLASK_APP_URL = os.environ.get('FLASK_APP_URL', 'https://candidate-summary-api-hdg54dp7ga-uc.a.run.app')
WORKER_VERSION = '1.0.0'

# Initialize Firestore
db = firestore.Client()

# Configuration
REQUEST_TIMEOUT = 60  # seconds

# --- REFACTORED: Renamed keys for clarity ---
# Fallback config if Firestore read fails
FALLBACK_CONFIG = {
    'use_quil': True,
    'include_fireflies': False,
    'proceed_without_interview': False,
    'additional_context': '',
    'prompt_type': 'summary-for-platform-v2',

    # Renamed from create_tracking_note
    'push_summary_to_candidate': False,

    # New flag for its original purpose
    'create_tracking_note': False,

    # Renamed from auto_push
    'move_to_next_stage': False,
    'auto_push_delay_seconds': 0 # We can rename this to move_stage_delay_seconds if you like
}