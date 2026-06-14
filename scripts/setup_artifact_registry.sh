#!/bin/bash
# One-time setup — run this once before the first push to main.
# Requires: gcloud CLI authenticated with an account that has roles/artifactregistry.admin
# Requires: .env file with GCP_PROJECT_ID, GCP_REGION, GCP_PROJECT_NUM set

set -e

# Load .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "Error: .env file not found. Run from project root." >&2
  exit 1
fi

# Validate required vars
: "${GCP_PROJECT_ID:?GCP_PROJECT_ID not set in .env}"
: "${GCP_REGION:?GCP_REGION not set in .env}"
: "${GCP_PROJECT_NUM:?GCP_PROJECT_NUM not set in .env}"

REPO="society-to-music"
SERVICE_ACCOUNT="${GCP_PROJECT_NUM}-compute@developer.gserviceaccount.com"

echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}" \
  --description="Society to Music pipeline images"

echo ""
echo "Granting service account push/pull access..."
gcloud artifacts repositories add-iam-policy-binding "${REPO}" \
  --location="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/artifactregistry.writer"

echo ""
echo "✓ Artifact Registry repository created"
echo "✓ Service account granted Artifact Registry writer role"
echo ""
echo "Image path:"
echo "  ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/pipeline"
