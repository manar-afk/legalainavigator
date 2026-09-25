#!/usr/bin/env bash
# Deploy Legal Information Navigator Backend to Google Cloud Run
set -euo pipefail

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-legal-ai-navigator}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-legal-navigator-backend}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "================================================================="
echo " Deploying Legal Information Navigator to Google Cloud Run"
echo " Project:  ${PROJECT_ID}"
echo " Region:   ${REGION}"
echo " Service:  ${SERVICE_NAME}"
echo " Image:    ${IMAGE_NAME}"
echo "================================================================="

# 1. Build Container Image with Google Cloud Build
echo "--> Building container image with Cloud Build..."
gcloud builds submit --project="${PROJECT_ID}" --tag="${IMAGE_NAME}" .

# 2. Deploy to Cloud Run
echo "--> Deploying service to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --image="${IMAGE_NAME}" \
    --platform="managed" \
    --allow-unauthenticated \
    --set-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY:-},USE_VERTEX_AI=${USE_VERTEX_AI:-false}" \
    --memory="1Gi" \
    --cpu="1" \
    --min-instances="0" \
    --max-instances="10" \
    --timeout="60s"

# 3. Output Service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)")

echo "================================================================="
echo " Successfully deployed to Google Cloud Run!"
echo " Service URL: ${SERVICE_URL}"
echo " Healthcheck: ${SERVICE_URL}/health"
echo " Evaluation:  ${SERVICE_URL}/api/evaluation/run"
echo " Docs:        ${SERVICE_URL}/docs"
echo "================================================================="
