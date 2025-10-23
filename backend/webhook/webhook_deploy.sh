#!/bin/bash

# Deployment script for the isolated webhook listener function (Google Cloud Functions)
set -e

# --- Configuration ---
PROJECT_ID="candidate-summary-ai"
FUNCTION_NAME="recruitcrm-webhook-listener"
REGION="us-central1"
RUNTIME="python312"  # Use a modern, supported runtime
ENTRY_POINT="webhook_listener" # <--- **CHANGE THIS**    # Name of the Flask application instance (or the function that handles the request)
SOURCE_DIR="webhook-listener" # Directory containing your Python function code
ACCOUNT_EMAIL="steve.waters@outstaffer.com"
# ---------------------

echo "🚀 Starting deployment for single webhook function..."

# --- Setup and Authentication (Same as your main script, for consistency) ---

echo "🔐 Setting Google account to $ACCOUNT_EMAIL..."
gcloud config set account $ACCOUNT_EMAIL

# Check if we need to authenticate (optional, but good practice)
if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" | grep -q "$ACCOUNT_EMAIL"; then
    echo "🔑 Account not authenticated. Running gcloud auth login..."
    gcloud auth login $ACCOUNT_EMAIL
fi

# Set the project
echo "📋 Setting Google Cloud project..."
gcloud config set project $PROJECT_ID

# --- Deploy the Function ---
echo "☁️ Deploying function: $FUNCTION_NAME in region $REGION..."

gcloud functions deploy $FUNCTION_NAME \
  --runtime $RUNTIME \
  --region $REGION \
  --entry-point $ENTRY_POINT \
  --source $SOURCE_DIR \
  --trigger-http \
  --allow-unauthenticated \
  --max-instances 1 \
  --min-instances 0 \
  --memory 256Mi \
  --timeout 60s

echo "✅ Deployment complete!"
echo " "
echo "➡️ To find the public URL and view logs, use the following commands:"
echo "   gcloud functions describe $FUNCTION_NAME --region $REGION --format='value(serviceConfig.uri)'"
echo "   gcloud functions logs read $FUNCTION_NAME --region $REGION --limit 50"