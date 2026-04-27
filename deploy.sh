#!/usr/bin/env bash
#
# Deploy the QKD API backend to Google Cloud Run.
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated (gcloud auth login)
#   2. A GCP project with billing enabled
#   3. Artifact Registry API and Cloud Run API enabled:
#        gcloud services enable artifactregistry.googleapis.com run.googleapis.com
#
# Usage:
#   ./deploy.sh                          # uses defaults
#   GCP_PROJECT=my-proj ./deploy.sh      # override project
#
set -euo pipefail

# ── Configuration (override via env vars) ────────────────────────────────────

PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-qkd-api}"
REPO_NAME="${REPO_NAME:-qkd-repo}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO_NAME}/${SERVICE_NAME}"

# GitHub Pages URL for CORS — update after first Pages deploy
GITHUB_PAGES_URL="${GITHUB_PAGES_URL:-https://john-jepsen.github.io}"

echo "==> Project:  ${PROJECT}"
echo "==> Region:   ${REGION}"
echo "==> Service:  ${SERVICE_NAME}"
echo "==> Image:    ${IMAGE}"
echo ""

# ── 1. Create Artifact Registry repo (idempotent) ───────────────────────────

echo "==> Ensuring Artifact Registry repo exists..."
gcloud artifacts repositories describe "${REPO_NAME}" \
  --location="${REGION}" --project="${PROJECT}" 2>/dev/null \
|| gcloud artifacts repositories create "${REPO_NAME}" \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT}" \
  --description="QKD container images"

# ── 2. Build & push with Cloud Build ────────────────────────────────────────

echo "==> Building and pushing container image..."
gcloud builds submit \
  --tag "${IMAGE}" \
  --project "${PROJECT}" \
  --timeout=600

# ── 3. Deploy to Cloud Run ──────────────────────────────────────────────────

echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "CORS_ORIGINS=${GITHUB_PAGES_URL},http://localhost:3000"

# ── 4. Print the service URL ────────────────────────────────────────────────

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" --project "${PROJECT}" \
  --format="value(status.url)")

echo ""
echo "=========================================="
echo " Deployed successfully!"
echo " API URL:  ${SERVICE_URL}"
echo " Health:   ${SERVICE_URL}/health"
echo " Docs:     ${SERVICE_URL}/docs"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Set GitHub repo variables for the frontend workflow:"
echo "     gh variable set VITE_API_URL --body '${SERVICE_URL}'"
echo "     gh variable set VITE_WS_URL  --body '${SERVICE_URL/https:/wss:}/ws/evolution'"
echo "  2. Push to main to trigger the GitHub Pages deploy"
echo "  3. Visit https://john-jepsen.github.io/qkd-avantheir/"
