#!/bin/bash

# Deployment script for the webhook listener function with Cloud Tasks support
set -e

# --- Configuration ---
PROJECT_ID="candidate-summary-ai"
FUNCTION_NAME="recruitcrm-webhook-listener"
REGION="us-central1"
RUNTIME="python312"
ENTRY_POINT="webhook_listener"
SOURCE_DIR="webhook-listener"
ACCOUNT_EMAIL="steve.waters@outstaffer.com"

# Cloud Tasks Configuration
CLOUD_TASKS_QUEUE="candidate-summary-queue"
CLOUD_TASKS_LOCATION="us-central1"

# IMPORTANT: Set this to your worker function URL after creating it in Phase 2
# Updated: 2024-10-27
WORKER_FUNCTION_URL="https://us-central1-candidate-summary-ai.cloudfunctions.net/summary-worker"

# ---------------------

echo "🚀 Starting deployment for webhook listener function..."

# --- Setup and Authentication ---
echo "🔐 Setting Google account to $ACCOUNT_EMAIL..."
gcloud config set account $ACCOUNT_EMAIL

# Check if we need to authenticate
if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" | grep -q "$ACCOUNT_EMAIL"; then
    echo "🔑 Account not authenticated. Running gcloud auth login..."
    gcloud auth login $ACCOUNT_EMAIL
fi

# Set the project
echo "📋 Setting Google Cloud project..."
gcloud config set project $PROJECT_ID

# --- Deploy the Function ---
echo "☁️ Deploying function: $FUNCTION_NAME in region $REGION..."
echo "📝 Environment variables:"
echo "   - GCP_PROJECT_ID: $PROJECT_ID"
echo "   - CLOUD_TASKS_QUEUE: $CLOUD_TASKS_QUEUE"
echo "   - CLOUD_TASKS_LOCATION: $CLOUD_TASKS_LOCATION"
echo "   - WORKER_FUNCTION_URL: $WORKER_FUNCTION_URL"

gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime $RUNTIME \
  --region $REGION \
  --entry-point $ENTRY_POINT \
  --source $SOURCE_DIR \
  --trigger-http \
  --allow-unauthenticated \
  --max-instances 10 \
  --min-instances 0 \
  --memory 256Mi \
  --timeout 60s \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,CLOUD_TASKS_QUEUE=$CLOUD_TASKS_QUEUE,CLOUD_TASKS_LOCATION=$CLOUD_TASKS_LOCATION,WORKER_FUNCTION_URL=$WORKER_FUNCTION_URL

echo "✅ Deployment complete!"
echo ""
echo "📍 Function URL:"
gcloud functions describe $FUNCTION_NAME --region $REGION --gen2 --format='value(serviceConfig.uri)'
echo ""
echo "📋 To view logs:"
echo "   gcloud functions logs read $FUNCTION_NAME --region $REGION --gen2 --limit 50"

