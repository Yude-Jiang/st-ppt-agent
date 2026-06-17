#!/usr/bin/env bash
# Usage: ./deploy.sh <environment>
set -euo pipefail

ENVIRONMENT="${1:-}"
PROJECT="st-china-ai-force"
REGION="asia-east1"
SERVICE="st-ppt-agent"
IMAGE="$REGION-docker.pkg.dev/$PROJECT/$SERVICE/$SERVICE"

if [[ -z "$ENVIRONMENT" ]]; then
  echo "Usage: $0 <staging|production>" >&2
  exit 1
fi

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
  echo "Unknown environment: $ENVIRONMENT. Must be 'staging' or 'production'." >&2
  exit 1
fi

# staging uses a separate Cloud Run service name with -staging suffix
if [[ "$ENVIRONMENT" == "staging" ]]; then
  SERVICE="st-ppt-agent-staging"
fi

TAG="$(git rev-parse --short HEAD)"
FULL_IMAGE="$IMAGE:$TAG"

echo "==> Deploying to $ENVIRONMENT (service=$SERVICE, image=$FULL_IMAGE)..."

# --- Pre-deploy checks ---
echo "==> Running pre-deploy checks..."
cd "$(dirname "$0")/../../.."
python -m pytest backend/tests/ -q --tb=short
echo "==> Tests passed."

# --- Build frontend ---
echo "==> Building frontend..."
cd frontend && npm run build && cd ..

# --- Build & push Docker image ---
echo "==> Building Docker image..."
gcloud builds submit \
  --project "$PROJECT" \
  --tag "$FULL_IMAGE" \
  .

# --- Deploy to Cloud Run ---
echo "==> Deploying to Cloud Run..."
gcloud run deploy "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$FULL_IMAGE" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --max-instances 1 \
  --set-env-vars "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-},GCS_BUCKET=st-ppt-agent-decks"

echo "==> Deploy to $ENVIRONMENT complete."
echo "==> Service URL: $(gcloud run services describe $SERVICE --project $PROJECT --region $REGION --format 'value(status.url)')"
