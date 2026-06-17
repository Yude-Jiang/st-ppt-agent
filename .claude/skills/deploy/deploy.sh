#!/usr/bin/env bash
# Usage: ./deploy.sh <environment>
# Deploys the application to the specified environment.

set -euo pipefail

ENVIRONMENT="${1:-}"

if [[ -z "$ENVIRONMENT" ]]; then
  echo "Usage: $0 <staging|production>" >&2
  exit 1
fi

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
  echo "Unknown environment: $ENVIRONMENT. Must be 'staging' or 'production'." >&2
  exit 1
fi

echo "==> Deploying to $ENVIRONMENT..."

# --- Pre-deploy checks ---
echo "==> Running pre-deploy checks..."
# TODO: replace with your actual lint/typecheck/test commands
# npm run lint
# npm run typecheck
# npm test -- --ci

# --- Build ---
echo "==> Building..."
# TODO: replace with your actual build command
# npm run build

# --- Deploy ---
echo "==> Pushing to $ENVIRONMENT..."
# TODO: replace with your actual deploy command, e.g.:
# fly deploy --config "fly.$ENVIRONMENT.toml"
# vercel deploy --env $ENVIRONMENT
# kubectl apply -f "k8s/$ENVIRONMENT/"

echo "==> Deploy to $ENVIRONMENT complete."
