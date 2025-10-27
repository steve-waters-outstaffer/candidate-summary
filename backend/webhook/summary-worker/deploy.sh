#!/bin/bash

# Deploy Summary Worker Cloud Function
# This function processes Cloud Tasks and orchestrates summary generation

# Configuration
PROJECT_ID="candidate-summary-ai"
FUNCTION_NAME="summary-worker"
REGION="us-central1"
RUNTIME="python311"
ENTRY_POINT="summary_worker"
MEMORY="512MB"
TIMEOUT="540s"  # 9 minutes (max for Cloud Functions)

# Environment variables
FLASK_APP_URL="https://candidate-summary-api-us-central1-candidate-summary-ai.run.app"

echo "🚀 Deploying Summary Worker Cloud Function..."
echo "📍 Region: $REGION"
echo "⚙️  Function: $FUNCTION_NAME"

# Deploy the function
gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=$RUNTIME \
  --region=$REGION \
  --source=. \
  --entry-point=$ENTRY_POINT \
  --trigger-http \
  --allow-unauthenticated \
  --memory=$MEMORY \
  --timeout=$TIMEOUT \
  --set-env-vars FLASK_APP_URL=$FLASK_APP_URL,GCP_PROJECT_ID=$PROJECT_ID \
  --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Copy the function URL from above"
    echo "2. Update webhook-listener environment variable WORKER_FUNCTION_URL"
    echo "3. Redeploy webhook-listener with the new URL"
    echo ""
    echo "🔍 View logs:"
    echo "gcloud functions logs read $FUNCTION_NAME --region=$REGION --project=$PROJECT_ID"
else
    echo "❌ Deployment failed"
    exit 1
fi
