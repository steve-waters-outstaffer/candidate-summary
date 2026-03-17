# AI Model Configurations

This document lists all locations in the codebase where AI model names are currently set. This is intended to assist in updating the models to the latest Gemini versions.

## Current Model Locations (Backend)

All AI model calls are currently located in the `backend/` directory.

### 1. Main HTML Summary Generation
- **File:** `backend/helpers/ai_helpers.py`
- **Line:** 166
- **Model:** `gemini-3-pro-preview`
- **Function:** `generate_ai_response(client, prompt_parts)`
- **Description:** This is the primary function used for generating HTML summaries for candidates.

### 2. Multi-Candidate Processing
- **File:** `backend/routes/multi.py`
- **Line:** 141
- **Model:** `gemini-3-flash-preview`
- **Function:** `process_curated_candidates()`
- **Description:** Used to process multiple candidates when generating combined summaries.

- **File:** `backend/routes/multi.py`
- **Line:** 240
- **Model:** `gemini-3-flash-preview`
- **Function:** `process_curated_candidates()` (inside the candidate loop)
- **Description:** Used for individual candidate processing within the multi-candidate flow.

### 3. Bulk Email Generation
- **File:** `backend/routes/bulk.py`
- **Line:** 335
- **Model:** `gemini-3-flash-preview`
- **Function:** `generate_bulk_email()`
- **Description:** Used when generating personalized emails in bulk for candidates.

### 4. Quil Interview Note Selection (Latest)
- **File:** `backend/helpers/quil_helpers.py`
- **Line:** 188
- **Model:** `gemini-3-flash-preview`
- **Function:** `select_best_quil_note_with_gemini()`
- **Description:** Selects the most relevant interview note from Quil for a specific job.

### 5. Quil Interview Note Processing (Old/Legacy)
- **File:** `backend/helpers/quil_helpers_old.py`
- **Line:** 90
- **Model:** `gemini-3-flash-preview`
- **Function:** `validate_quil_notes_with_gemini()`
- **Description:** Validates and cleans up Quil interview notes.

- **File:** `backend/helpers/quil_helpers_old.py`
- **Line:** 237
- **Model:** `gemini-3-flash-preview`
- **Function:** `match_quil_note_to_job()`
- **Description:** Matches a Quil note to a specific job description.

## Summary of Models Used
- `gemini-3-pro-preview`: Used for the core summary generation (highest quality).
- `gemini-3-flash-preview`: Used for multi-candidate, bulk, and Quil processing (fast + cost-effective).

## Frontend Check
No direct AI model calls or model name configurations were found in the `src/` or `public/` directories. All AI processing is handled by the backend API.

## Model Reference
- **Gemini 3 Pro Preview** (`gemini-3-pro-preview`): State-of-the-art reasoning, best for complex generation tasks.
- **Gemini 3 Flash Preview** (`gemini-3-flash-preview`): Pro-grade reasoning at Flash speed/cost, best for high-volume/latency-sensitive tasks.
- Both models are currently in preview (as of Feb 2026). Monitor for stable releases.
