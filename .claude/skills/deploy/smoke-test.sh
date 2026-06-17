#!/usr/bin/env bash
# Usage: ./smoke-test.sh <environment>
# Runs basic health checks against a deployed environment.

set -euo pipefail

ENVIRONMENT="${1:-}"

if [[ -z "$ENVIRONMENT" ]]; then
  echo "Usage: $0 <staging|production>" >&2
  exit 1
fi

# --- Environment URLs ---
# TODO: replace with your actual base URLs
case "$ENVIRONMENT" in
  staging)    BASE_URL="https://staging.example.com" ;;
  production) BASE_URL="https://example.com" ;;
  *)
    echo "Unknown environment: $ENVIRONMENT" >&2
    exit 1
    ;;
esac

echo "==> Smoke testing $ENVIRONMENT at $BASE_URL..."

PASS=0
FAIL=0

check() {
  local description="$1"
  local url="$2"
  local expected_status="${3:-200}"

  actual_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" || echo "000")

  if [[ "$actual_status" == "$expected_status" ]]; then
    echo "  [PASS] $description ($url → $actual_status)"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $description ($url → $actual_status, expected $expected_status)"
    FAIL=$((FAIL + 1))
  fi
}

# --- Generic checks (always run) ---
check "Health endpoint"   "$BASE_URL/health"
check "Home page loads"   "$BASE_URL/"

# --- TODO: Project-specific checks ---
# Add checks for critical pages and API routes specific to this project.
# Examples:
#
# check "Login page"                  "$BASE_URL/login"
# check "API status"                  "$BASE_URL/api/v1/status"
# check "Missing route returns 404"   "$BASE_URL/this-should-not-exist" "404"
#
# For checks that require authentication or POST bodies, use:
# actual=$(curl -s -X POST "$BASE_URL/api/v1/ping" \
#   -H "Authorization: Bearer $SMOKE_TEST_TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"ping":true}')
# [[ "$actual" == *"pong"* ]] && echo "[PASS] ping/pong" || echo "[FAIL] ping/pong"

# --- Summary ---
echo ""
echo "==> Results: $PASS passed, $FAIL failed"

if [[ $FAIL -gt 0 ]]; then
  echo "==> SMOKE TEST FAILED" >&2
  exit 1
fi

echo "==> Smoke tests passed."
