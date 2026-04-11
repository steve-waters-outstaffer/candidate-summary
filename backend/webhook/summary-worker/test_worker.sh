#!/bin/bash

# Test the summary worker locally or in Cloud

# Test candidate and job slugs
CANDIDATE_SLUG="your-candidate-slug-here"
JOB_SLUG="your-job-slug-here"

# Worker URL (update after deployment)
WORKER_URL="https://us-central1-candidate-summary-ai.cloudfunctions.net/summary-worker"

# Create test payload
PAYLOAD=$(cat <<EOF
{
  "candidate_slug": "$CANDIDATE_SLUG",
  "job_slug": "$JOB_SLUG",
  "webhook_payload": {
    "test": true
  }
}
EOF
)

echo "🧪 Testing Summary Worker"
echo "📋 Candidate: $CANDIDATE_SLUG"
echo "💼 Job: $JOB_SLUG"
echo ""
echo "📤 Sending request..."

# Send the request
curl -X POST $WORKER_URL \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  -w "\n\n⏱️  Response time: %{time_total}s\n" \
  -s | jq .

echo ""
echo "✅ Test complete"
echo ""
echo "🔍 Check Firestore collection: candidate_summary_runs"
echo "🔍 View logs: gcloud functions logs read summary-worker --region=us-central1 --limit=50"
