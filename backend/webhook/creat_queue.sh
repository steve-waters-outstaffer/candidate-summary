#!/bin/bash

# Create Cloud Tasks Queue for Candidate Summary Automation
# Run this script to set up the queue in your GCP project

# Configuration
PROJECT_ID="candidate-summary-ai"  # Replace with your GCP project ID
QUEUE_NAME="candidate-summary-queue"
LOCATION="us-central1"  # Replace with your preferred region

# Create the queue
gcloud tasks queues create $QUEUE_NAME \
  --location=$LOCATION \
  --max-dispatches-per-second=5 \
  --max-concurrent-dispatches=10 \
  --max-attempts=3 \
  --min-backoff=10s \
  --max-backoff=300s \
  --project=$PROJECT_ID

echo "✅ Cloud Tasks queue created: $QUEUE_NAME"
echo "📍 Location: $LOCATION"
echo "🔧 Max rate: 5 dispatches/sec"
echo "🔁 Max retries: 3 attempts"

# Verify the queue was created
echo ""
echo "Verifying queue creation..."
gcloud tasks queues describe $QUEUE_NAME \
  --location=$LOCATION \
  --project=$PROJECT_ID


