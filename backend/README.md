# Candidate Summary Generator - Backend

Flask API server for generating AI-powered candidate summaries.

## Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Environment Configuration:**
   ```bash
   cp .env.example .env
   ```
   
   Update `.env` with your API keys:
   ```
   GOOGLE_API_KEY=your_google_gemini_api_key
   RECRUITCRM_API_KEY=your_recruitcrm_bearer_token
   ALPHARUN_API_KEY=your_alpharun_bearer_token
   ```

3. **Run Development Server:**
   ```bash
   python app.py
   ```
   
   Server runs on `http://localhost:5000`

## API Endpoints

### POST `/api/generate-summary`
Generate candidate summary from URLs and interview ID.

**Request:**
```json
{
  "candidate_url": "https://app.recruitcrm.io/candidates/010011",
  "job_url": "https://app.recruitcrm.io/jobs/121", 
  "interview_id": "abc123",
  "additional_context": "Optional extra context..."
}
```

**Response:**
```json
{
  "success": true,
  "html_summary": "<style>...</style><div>...</div>",
  "candidate_slug": "010011"
}
```

### POST `/api/push-to-recruitcrm`
Push generated summary to RecruitCRM candidate record.

**Request:**
```json
{
  "candidate_slug": "010011",
  "html_summary": "<style>...</style><div>...</div>"
}
```

### POST `/api/webhooks/recruitcrm`
Accept webhook callbacks from RecruitCRM when a candidate advances to Stage 3.

**Request:**
```json
{
  "event": "stage.moved",
  "data": {
    "candidate_slug": "candidate-123",
    "job_slug": "job-456",
    "stage": {
      "id": 3,
      "name": "Stage 3"
    }
  }
}
```

- The server immediately acknowledges the request with `{ "status": "accepted" }` and HTTP `200`.
- Processing continues asynchronously: the worker reuses the single-candidate summary pipeline, appends an automated Stage 3 note, and updates the candidate record via `push_to_recruitcrm_internal`.
- Payloads missing Stage 3 context are acknowledged but skipped after logging.

## Deployment

For production deployment to Google Cloud Run:

1. **Build Docker image:**
   ```bash
   docker build -t candidate-summary-api .
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy candidate-summary-api \
     --image candidate-summary-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars GOOGLE_API_KEY=xxx,RECRUITCRM_API_KEY=xxx,ALPHARUN_API_KEY=xxx
   ```

## Environment Variables

- `GOOGLE_API_KEY` - Google Gemini API key for AI generation
- `RECRUITCRM_API_KEY` - RecruitCRM Bearer token
- `ALPHARUN_API_KEY` - AlphaRun Bearer token  
- `FLASK_ENV` - Set to 'production' for production deployment
