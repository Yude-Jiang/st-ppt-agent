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
  staging)    BASE_URL="https://st-ppt-agent-staging-PLACEHOLDER.asia-east1.run.app" ;;
  production) BASE_URL="https://st-ppt-agent-PLACEHOLDER.asia-east1.run.app" ;;
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

# --- Project-specific checks: ST PPT Agent ---

# API 路由存在性
check "Tasks API route exists"         "$BASE_URL/api/tasks" "405"   # POST-only, GET → 405
check "404 for unknown route"          "$BASE_URL/api/nonexistent" "404"

# 前端页面（React SPA，路由由前端处理，服务端返回 200 + index.html）
check "Home page (文案输入页)"          "$BASE_URL/"
check "Review page shell"              "$BASE_URL/review"

# 异步任务：提交一个最简文案，验证任务 ID 能返回（不等待完成）
SUBMIT_RESP=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE_URL/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{"text":"ST MCU 产品介绍","target_slides":3}' \
  --max-time 15 || echo "000")

if [[ "$SUBMIT_RESP" == "202" ]]; then
  echo "  [PASS] Task submission returns 202 ($BASE_URL/api/tasks)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] Task submission returned $SUBMIT_RESP, expected 202 ($BASE_URL/api/tasks)"
  FAIL=$((FAIL + 1))
fi

# 任务状态查询路由存在（用不存在的 task_id，期望 404 而非 500）
check "Task status route (unknown id)" "$BASE_URL/api/tasks/smoke-test-nonexistent-id" "404"

# --- Summary ---
echo ""
echo "==> Results: $PASS passed, $FAIL failed"

if [[ $FAIL -gt 0 ]]; then
  echo "==> SMOKE TEST FAILED" >&2
  exit 1
fi

echo "==> Smoke tests passed."
