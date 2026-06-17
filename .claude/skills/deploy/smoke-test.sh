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

# Cloud Run 冷启动 + 跨境网络可能偏慢，给足余量（DeepSeek review: 原 10s 偏紧）
CURL_TIMEOUT=20

check() {
  local description="$1"
  local url="$2"
  local expected_status="${3:-200}"
  local expected_content_type="${4:-}"  # 可选：要求响应头包含此 Content-Type 子串

  local resp
  resp=$(curl -s -D - -o /tmp/smoke_body.$$ -w "\n%{http_code}" --max-time "$CURL_TIMEOUT" "$url" 2>/dev/null || echo -e "\n000")
  local actual_status
  actual_status=$(echo "$resp" | tail -n1)
  local headers
  headers=$(echo "$resp" | sed '$d')
  rm -f /tmp/smoke_body.$$

  if [[ "$actual_status" != "$expected_status" ]]; then
    echo "  [FAIL] $description ($url → $actual_status, expected $expected_status)"
    FAIL=$((FAIL + 1))
    return
  fi

  if [[ -n "$expected_content_type" ]] && ! echo "$headers" | grep -qi "content-type:.*$expected_content_type"; then
    echo "  [FAIL] $description ($url → $actual_status OK, but Content-Type missing '$expected_content_type')"
    FAIL=$((FAIL + 1))
    return
  fi

  echo "  [PASS] $description ($url → $actual_status)"
  PASS=$((PASS + 1))
}

# 从 JSON body 里提取一个字符串字段的值，不依赖 jq（DeepSeek review 问题2/4：
# Cloud Run 基础镜像不一定装了 jq，smoke-test 作为"安全绳"本身不该有这种外部依赖）
# 注意: grep -o 在无匹配时返回非零退出码，在 set -e 下会让整个脚本提前退出，
# 而不是让调用方拿到空字符串继续判断 —— 这里必须显式 `|| true` 吞掉那个退出码。
extract_json_field() {
  local json="$1"
  local field="$2"
  echo "$json" | grep -o "\"$field\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" 2>/dev/null | head -n1 | sed -E "s/.*:\s*\"([^\"]*)\"/\1/" || true
}

# --- Generic checks (always run) ---
check "Health endpoint" "$BASE_URL/health"
check "Home page loads (Content-Type: text/html)" "$BASE_URL/" "200" "text/html"

# --- Project-specific checks: ST PPT Agent ---

# API 路由存在性
check "Tasks API route exists (GET not allowed)" "$BASE_URL/api/tasks" "405"
check "404 for unknown route" "$BASE_URL/api/nonexistent" "404"

# 前端页面（React SPA，路由由前端处理，服务端返回 200 + index.html）
check "Review page shell" "$BASE_URL/review"

# --- 异步任务端到端链路：提交 → 解析 task_id → 用真实 id 查状态 ---
# DeepSeek review 问题2/3：原版只检查提交的状态码，没有验证 task_id 能否被实际
# 用于后续查询；且避免重复提交（幂等性风险），一次请求同时拿状态码和 body。
TASK_RESP=$(curl -s -w "\n%{http_code}" --max-time "$CURL_TIMEOUT" \
  -X POST "$BASE_URL/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{"text":"ST MCU 产品介绍","target_slides":3}' 2>/dev/null || echo -e "\n000")
TASK_HTTP_CODE=$(echo "$TASK_RESP" | tail -n1)
TASK_BODY=$(echo "$TASK_RESP" | sed '$d')

if [[ "$TASK_HTTP_CODE" == "202" ]]; then
  TASK_ID=$(extract_json_field "$TASK_BODY" "task_id")
  if [[ -n "$TASK_ID" ]]; then
    echo "  [PASS] Task submission returns 202 with task_id ($BASE_URL/api/tasks)"
    PASS=$((PASS + 1))
    check "Task status returns 200 for real task_id" "$BASE_URL/api/tasks/$TASK_ID" "200"
  else
    echo "  [FAIL] Task submission returned 202 but response body missing task_id field (body: $TASK_BODY)"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  [FAIL] Task submission returned $TASK_HTTP_CODE, expected 202 ($BASE_URL/api/tasks)"
  FAIL=$((FAIL + 1))
fi

# 未知 task_id 应返回 404 而非 500
check "Task status route (unknown id)" "$BASE_URL/api/tasks/smoke-test-nonexistent-id" "404"

# 用于负面用例：只关心状态码的 POST 请求，统一处理连接失败的情况
# （避免 -w 在连接失败时输出空字符串 + || echo "000" fallback 叠加成 "000000"）
post_status_only() {
  local url="$1"
  local data="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$CURL_TIMEOUT" \
    -X POST "$url" -H "Content-Type: application/json" -d "$data" 2>/dev/null)
  [[ -z "$code" ]] && code="000"
  echo "$code"
}

# --- 负面用例：参数校验 ---
# DeepSeek review 问题5：这些比单纯的 404 检查更能暴露入参校验的缺失。
# 注意：这要求 BUILD 阶段后端已实现对应的校验逻辑，否则这里会如实报 FAIL。
NEGATIVE_EMPTY=$(post_status_only "$BASE_URL/api/tasks" '{}')
if [[ "$NEGATIVE_EMPTY" == "400" ]]; then
  echo "  [PASS] Empty body rejected with 400 ($BASE_URL/api/tasks)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] Empty body returned $NEGATIVE_EMPTY, expected 400 ($BASE_URL/api/tasks)"
  FAIL=$((FAIL + 1))
fi

NEGATIVE_NO_TEXT=$(post_status_only "$BASE_URL/api/tasks" '{"target_slides":3}')
if [[ "$NEGATIVE_NO_TEXT" == "400" ]]; then
  echo "  [PASS] Missing 'text' field rejected with 400 ($BASE_URL/api/tasks)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] Missing 'text' field returned $NEGATIVE_NO_TEXT, expected 400 ($BASE_URL/api/tasks)"
  FAIL=$((FAIL + 1))
fi

NEGATIVE_ZERO_SLIDES=$(post_status_only "$BASE_URL/api/tasks" '{"text":"ST MCU 产品介绍","target_slides":0}')
if [[ "$NEGATIVE_ZERO_SLIDES" == "400" ]]; then
  echo "  [PASS] target_slides=0 rejected with 400 ($BASE_URL/api/tasks)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] target_slides=0 returned $NEGATIVE_ZERO_SLIDES, expected 400 ($BASE_URL/api/tasks)"
  FAIL=$((FAIL + 1))
fi

# --- Summary ---
echo ""
echo "==> Results: $PASS passed, $FAIL failed"

if [[ $FAIL -gt 0 ]]; then
  echo "==> SMOKE TEST FAILED" >&2
  exit 1
fi

echo "==> Smoke tests passed."
