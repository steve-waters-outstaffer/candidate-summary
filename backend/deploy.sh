#!/bin/bash

# Simple deployment script for Cloud Run
set -e

# Configuration
PROJECT_ID="candidate-summary-ai"
SERVICE_NAME="candidate-summary-api"
REGION="us-central1"  # Change if you prefer different region
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
ACCOUNT_EMAIL="steve.waters@outstaffer.com"

echo "🚀 Starting deployment..."

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "📋 Loaded environment variables from .env"
else
    echo "❌ .env file not found!"
    exit 1
fi

# Set the correct Google account
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

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME .

# Push to Google Container Registry
echo "📤 Pushing image to Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run with extended timeout and resources
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 4 \
  --timeout 3600 \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 5 \
  --port 5000 \
  --execution-environment gen2 \
  --set-env-vars FLASK_ENV=production \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY \
  --set-env-vars RECRUITCRM_API_KEY=$RECRUITCRM_API_KEY \
  --set-env-vars ALPHARUN_API_KEY=$ALPHARUN_API_KEY

echo "✅ Deployment complete!"
echo "🌐 Service URL: https://$SERVICE_NAME-$REGION-$PROJECT_ID.run.app"