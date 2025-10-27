# Summary Worker Cloud Function

Processes Cloud Tasks from the webhook listener and orchestrates candidate summary generation.

## Architecture

```
Cloud Tasks Queue
    ↓
Summary Worker (this function)
    ↓
Flask App (/api endpoints)
    ↓
Firestore (logs)
```

## What It Does

1. Receives task from Cloud Tasks with `candidate_slug` and `job_slug`
2. Tests endpoints in sequence (mirrors UI flow):
   - **BLOCKING:** Candidate Data, Job Data
   - **OPTIONAL:** CV Data, AI Interview, Quil Interview
3. Generates summary with available sources
4. Logs full run data to Firestore collection `candidate_summary_runs`

## Configuration

**Default Settings:**
- `useQuil: true`
- `auto_push: false` (Phase 3 will add push with tracking note)
- `includeFireflies: false`
- Proceeds without Anna AI interview

## Deployment

```bash
# From this directory
chmod +x deploy.sh
./deploy.sh
```

**After deployment:**
1. Copy the function URL from deployment output
2. Update webhook-listener with `WORKER_FUNCTION_URL`
3. Redeploy webhook-listener

## Environment Variables

Set in Cloud Function:
- `FLASK_APP_URL` - Flask app endpoint (Cloud Run URL)
- `GCP_PROJECT_ID` - Your GCP project ID

Auto-available:
- Firestore credentials (via Cloud Function runtime)
- Task metadata (via HTTP headers)

## Testing

### Manual Test (after deployment)
```bash
# Edit test_worker.sh with real slugs
chmod +x test_worker.sh
./test_worker.sh
```

### Manual Trigger via gcloud
```bash
gcloud functions call summary-worker \
  --region=us-central1 \
  --data '{
    "candidate_slug": "your-slug",
    "job_slug": "your-job"
  }'
```

### Check Logs
```bash
gcloud functions logs read summary-worker \
  --region=us-central1 \
  --limit=50
```

## Firestore Logging

Every run logs to `candidate_summary_runs` collection:

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "candidate_slug": "...",
  "job_slug": "...",
  
  "tests": {
    "candidate_data": { "success": true, "error": null },
    "job_data": { "success": true, "error": null },
    "cv_data": { "success": true, "error": null },
    "ai_interview": { "success": false, "error": "Not found" },
    "quil_interview": { 
      "success": true, 
      "error": null,
      "note_id": "123456"
    }
  },
  
  "sources_used": {
    "resume": true,
    "anna_ai": false,
    "quil": true,
    "fireflies": false
  },
  
  "generation": {
    "success": true,
    "summary_length": 1234,
    "duration_seconds": 8.5,
    "error": null
  },
  
  "worker_metadata": {
    "cloud_task_id": "...",
    "worker_version": "1.0.0",
    "retry_attempt": 0,
    "triggered_by": {
      "id": 115953,
      "email": "adele.fernandez@outstaffer.com",
      "first_name": "Adele",
      "last_name": "Fernandez"
    }
  }
}
```

## Error Handling

**Blocking Errors (stops processing):**
- Candidate data not found → 400 (no retry)
- Job data not found → 400 (no retry)

**Optional Errors (continues processing):**
- CV data not available → logs warning, continues
- AI interview not available → logs warning, continues
- Quil interview not available → logs warning, continues

**Retriable Errors:**
- Network timeouts → 500 (Cloud Tasks retries)
- API rate limits → 500 (Cloud Tasks retries)
- Summary generation fails → 500 (Cloud Tasks retries)

## Monitoring

**Key Metrics:**
- Task processing time
- Source availability rates
- Success/failure rates
- Retry attempts

**Query Firestore for stats:**
```javascript
// Success rate
db.collection('candidate_summary_runs')
  .where('generation.success', '==', true)
  .get()

// Source usage breakdown
db.collection('candidate_summary_runs')
  .where('sources_used.quil', '==', true)
  .get()
```

## Next Phase

Phase 3 will add:
- Summary tracking note to RecruitCRM
- Push summary to RCRM after generation
- Enhanced metadata in tracking note

## TODO: Notifications

Currently captures `updated_by` from webhook payload:
```json
{
  "id": 115953,
  "email": "adele.fernandez@outstaffer.com",
  "first_name": "Adele",
  "last_name": "Fernandez"
}
```

**Future notification options:**

1. **Slack Integration**
   - Post to #recruitment channel
   - Success: "✅ Summary generated for [candidate] / [job] by Adele"
   - Failure: "❌ Summary failed for [candidate] - [error]"
   - Include: Sources used, generation time, link to RecruitCRM

2. **Email Notification**
   - Send to `updated_by.email`
   - Only on failures or configurable

3. **RecruitCRM Activity Feed**
   - Webhook back to RecruitCRM
   - Shows in candidate timeline

**Implementation location:** `send_slack_notification()` function (TODO in main.py)
