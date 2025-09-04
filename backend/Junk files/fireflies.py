#!/usr/bin/env python3
"""
fetch_fireflies_transcript.py

A command-line tool to fetch and process a transcript from Fireflies.ai.

This script will prompt you to enter your API key and the transcript URL
when you run it.

- Fetches a transcript by its ID or full URL.
- Normalises the transcript JSON into a format suitable for LLMs.
- Outputs the normalised JSON to stdout and saves it to a local file.
"""

import json
import os
import re
import sys
from getpass import getpass
from urllib.parse import urlparse
import requests

# --- Constants ---
GRAPHQL_URL = "https://api.fireflies.ai/graphql"
# Fireflies IDs are ULID-like (26 chars, Crockford base32 without I,L,O,U)
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

TRANSCRIPT_QUERY = """
query Transcript($id: String!) {
  transcript(id: $id) {
    id
    title
    date
    duration
    transcript_url
    speakers { id name }
    sentences {
      index
      speaker_name
      start_time
      end_time
      text
      raw_text
    }
  }
}
"""

# --- Core Functions ---

def extract_transcript_id(s: str) -> str | None:
    """
    Parses a string to find a Fireflies transcript ID.

    Args:
        s: The input string, which can be a full URL or a standalone ID.

    Returns:
        The extracted 26-character ID, or None if not found.
    """
    s = s.strip()
    # If user pasted a full URL, parse ".../view/<slug>::<ID>"
    if s.startswith("http://") or s.startswith("https://"):
        try:
            path_segment = urlparse(s).path.rsplit("/", 1)[-1]
            parts = path_segment.split("::")
            if len(parts) == 2 and ULID_PATTERN.fullmatch(parts[1]):
                return parts[1]
        except (IndexError, ValueError):
            return None
        return None
    # If they pasted just the ID
    if ULID_PATTERN.fullmatch(s):
        return s
    return None

def graphql_post(api_key: str, query: str, variables: dict) -> dict:
    """
    Executes a POST request to the Fireflies GraphQL API.

    Args:
        api_key: The Fireflies API key for authentication.
        query: The GraphQL query string.
        variables: A dictionary of variables for the query.

    Returns:
        A dictionary containing the response data or error information.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        payload = resp.json()

        if "errors" in payload:
            # Return the whole payload so the caller can show precise error messages
            return {"ok": False, "status": resp.status_code, "errors": payload["errors"]}

        return {"ok": True, "status": resp.status_code, "data": payload.get("data")}

    except requests.exceptions.RequestException as e:
        return {"ok": False, "status": "RequestError", "errors": [str(e)]}
    except json.JSONDecodeError:
        return {"ok": False, "status": "JSONError", "errors": ["Failed to decode JSON response."]}


def normalise_for_llm(tr: dict) -> dict:
    """
    Produces a compact, LLM-ready JSON from the raw transcript data.

    Args:
        tr: The raw transcript dictionary from the API.

    Returns:
        A normalised dictionary with metadata, sentences, and full content string.
    """
    speakers = [s.get("name") for s in (tr.get("speakers") or []) if s and s.get("name")]
    sentences = []
    lines = []
    for s in (tr.get("sentences") or []):
        entry = {
            "i": s.get("index"),
            "speaker": s.get("speaker_name"),
            "start": s.get("start_time"),
            "end": s.get("end_time"),
            "text": s.get("text"),
        }
        sentences.append(entry)
        speaker = entry["speaker"] or "Unknown"
        text = entry["text"] or ""
        lines.append(f"{speaker}: {text}".strip())

    return {
        "metadata": {
            "id": tr.get("id"),
            "title": tr.get("title"),
            "date": tr.get("date"),
            "duration_seconds": tr.get("duration"),
            "url": tr.get("transcript_url"),
            "speakers": speakers,
            "sentence_count": len(sentences),
        },
        "sentences": sentences,
        "content": "\n".join(lines),
    }

def main():
    """Main execution function."""
    print("=== Fireflies Transcript Fetcher ===")

    # 1. Get API Key
    api_key = os.getenv("FIREFLIES_API_KEY")
    if not api_key:
        try:
            api_key = getpass("Paste your Fireflies API key (input hidden): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.", file=sys.stderr)
            sys.exit(1)

    if not api_key:
        print("Error: API key is required.", file=sys.stderr)
        sys.exit(1)

    # 2. Get Transcript ID
    raw_id = ""
    try:
        raw_id = input("Paste Transcript ID or Fireflies URL: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(1)

    transcript_id = extract_transcript_id(raw_id)
    if not transcript_id:
        print("Error: Could not parse a valid Transcript ID. Make sure you provide the 26-char ID or a full URL containing '::ID'.", file=sys.stderr)
        sys.exit(1)

    # 3. Fetch and Process
    print(f"Fetching transcript {transcript_id} ...")
    res = graphql_post(api_key, TRANSCRIPT_QUERY, {"id": transcript_id})

    if not res.get("ok"):
        print("API Error:", file=sys.stderr)
        print(json.dumps(res, indent=2), file=sys.stderr)
        sys.exit(2)

    tr = res.get("data", {}).get("transcript")
    if not tr:
        print("Error: No transcript data found for that ID in the API response.", file=sys.stderr)
        sys.exit(3)

    # 4. Normalise and Output
    normalised_output = normalise_for_llm(tr)

    # Save to file
    out_path = f"transcript_{transcript_id}.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(normalised_output, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully saved transcript to: {out_path}")
    except IOError as e:
        print(f"\nError saving file to {out_path}: {e}", file=sys.stderr)

    # Print to stdout
    print("\n--- Normalised Transcript ---")
    print(json.dumps(normalised_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
