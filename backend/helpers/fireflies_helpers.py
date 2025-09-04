# helpers/fireflies_helpers.py
import os
import re
import requests
import structlog
from urllib.parse import urlparse
from flask import json

log = structlog.get_logger()

FIREFLIES_API_KEY = os.getenv('FIREFLIES_API_KEY')
GRAPHQL_URL = "https://api.fireflies.ai/graphql"
TRANSCRIPT_QUERY = """
query Transcript($id: String!) {
  transcript(id: $id) {
    id
    title
    transcript_url
    speakers { id name }
    sentences { speaker_name text }
  }
}
"""
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

def get_fireflies_headers():
    """Returns the authorization headers for the Fireflies.ai API."""
    if not FIREFLIES_API_KEY:
        raise ValueError("FIREFLIES_API_KEY is not set in the environment.")
    return {
        'Authorization': f'Bearer {FIREFLIES_API_KEY}',
        'Content-Type': 'application/json'
    }

def extract_fireflies_transcript_id(s: str) -> str | None:
    """Parses a string to find a Fireflies transcript ID."""
    if not s:
        return None
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

def fetch_fireflies_transcript(transcript_id: str) -> dict | None:
    """Fetches a transcript from Fireflies.ai using GraphQL."""
    payload = {"query": TRANSCRIPT_QUERY, "variables": {"id": transcript_id}}
    try:
        resp = requests.post(GRAPHQL_URL, json=payload, headers=get_fireflies_headers(), timeout=30)
        resp.raise_for_status()
        response_data = resp.json()
        if "errors" in response_data:
            log.error("fireflies.fetch_transcript.graphql_error", transcript_id=transcript_id)
            return None
        return response_data.get("data", {}).get("transcript")
    except requests.exceptions.RequestException as e:
        log.error("fireflies.fetch_transcript.request_error", transcript_id=transcript_id, error=str(e))
        return None
    except json.JSONDecodeError:
        log.error("fireflies.fetch_transcript.json_decode_error", transcript_id=transcript_id)
        return None

def normalise_fireflies_transcript(raw_transcript):
    """Normalises raw Fireflies transcript data into a structured format."""
    if not raw_transcript:
        return {'metadata': {}, 'content': "Not provided."}

    title = raw_transcript.get('title', 'N/A')
    sentences = raw_transcript.get('sentences', [])
    content = '\n'.join([f"{s.get('speaker_name', 'Unknown')}: {s.get('text', '')}" for s in sentences])

    return {
        'metadata': {'title': title},
        'content': content or "Transcript content is empty."
    }