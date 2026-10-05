#!/usr/bin/env bash
# End-to-end acceptance against the isolated test topology (blueprint 10 §2).
#
# Requires: bash, docker compose, curl (Linux / macOS / WSL / Git Bash on Windows).
# Starts the compose.test overlay with fresh secrets, applies migrations with
# the single controlled executor, mints dev/test tokens through the backend
# CLI, exercises the HTTP contract (problem shapes, authz, idempotency) and
# tears everything down, volumes included.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT="project-test"
COMPOSE=(docker compose -f "$ROOT/infra/compose/compose.yaml" -f "$ROOT/infra/compose/compose.test.yaml" -p "$PROJECT")
export E2E_API_PORT="${E2E_API_PORT:-18000}"
API="http://127.0.0.1:${E2E_API_PORT}/api/v1"
WORK="$(mktemp -d)"

cleanup() {
  echo "[e2e] tearing down"
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

random_hex() { head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'; }
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(random_hex 32)}"
export JWT_SECRET="${JWT_SECRET:-$(random_hex 32)}"

fail() { echo "[e2e] FAIL: $1"; exit 1; }

# request METHOD PATH [TOKEN] [JSON_BODY] [EXTRA_HEADER] -> sets STATUS, BODY_FILE, HDR_FILE
N=0
request() {
  local method="$1" path="$2" token="${3:-}" body="${4:-}" extra="${5:-}"
  N=$((N + 1))
  BODY_FILE="$WORK/body.$N"
  HDR_FILE="$WORK/hdr.$N"
  local args=(-s -o "$BODY_FILE" -D "$HDR_FILE" -w "%{http_code}" -X "$method")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  [ -n "$body" ] && args+=(-H "Content-Type: application/json" --data "$body")
  [ -n "$extra" ] && args+=(-H "$extra")
  STATUS="$(curl "${args[@]}" "$API$path")"
}

expect_status() { [ "$STATUS" = "$1" ] || fail "$2: expected $1, got $STATUS ($(cat "$BODY_FILE"))"; }
expect_code() { grep -q "\"code\":\"$1\"" "$BODY_FILE" || fail "$2: body lacks code $1 ($(cat "$BODY_FILE"))"; }
expect_problem_type() {
  grep -qi '^content-type: application/problem+json' "$HDR_FILE" || fail "$1: not application/problem+json"
}
json_field() { sed -n "s/.*\"$1\":\"\([^\"]*\)\".*/\1/p" "$BODY_FILE"; }

echo "[e2e] building api image"
"${COMPOSE[@]}" build api >/dev/null

echo "[e2e] starting postgres + redis"
"${COMPOSE[@]}" up -d --wait postgres redis >/dev/null

echo "[e2e] applying migrations (single executor)"
"${COMPOSE[@]}" run --rm --no-deps api alembic upgrade head >/dev/null

echo "[e2e] starting api"
"${COMPOSE[@]}" up -d --no-build api >/dev/null

echo "[e2e] waiting for API health"
for i in $(seq 1 60); do
  if curl -sf "$API/health" >/dev/null 2>&1; then break; fi
  [ "$i" = 60 ] && fail "API never became healthy"
  sleep 2
done

mint() { "${COMPOSE[@]}" exec -T api python -m project_backend.entrypoints.cli mint-token "$@" | tr -d '\r\n'; }
EDITOR="$(mint --subject e2e-editor --role editor)"
VIEWER="$(mint --subject e2e-viewer --role viewer)"
[ -n "$EDITOR" ] && [ -n "$VIEWER" ] || fail "could not mint tokens"

echo "[e2e] health contract"
request GET /health
expect_status 200 "health"
grep -q '"status":"ok"' "$BODY_FILE" || fail "health body"

echo "[e2e] unauthenticated -> 401 AUTHN.REQUIRED"
request GET /resources
expect_status 401 "unauthenticated list"
expect_code AUTHN.REQUIRED "unauthenticated list"
expect_problem_type "unauthenticated list"

echo "[e2e] invalid token -> 401 AUTHN.INVALID"
request GET /resources "not.a.token"
expect_status 401 "invalid token"
expect_code AUTHN.INVALID "invalid token"

echo "[e2e] viewer write -> 403 AUTHZ.DENIED"
request POST /resources "$VIEWER" '{"name":"e2e-denied"}'
expect_status 403 "viewer create"
expect_code AUTHZ.DENIED "viewer create"

echo "[e2e] validation -> 422 VALIDATION.FAILED"
request POST /resources "$EDITOR" '{"name":""}'
expect_status 422 "empty name"
expect_code VALIDATION.FAILED "empty name"
expect_problem_type "empty name"

echo "[e2e] missing resource -> 404 NOT.FOUND"
request GET /resources/does-not-exist "$EDITOR"
expect_status 404 "missing resource"
expect_code NOT.FOUND "missing resource"

echo "[e2e] idempotent create -> 201, replay -> 201 same id"
KEY="e2e-$(random_hex 16)"
request POST /resources "$EDITOR" '{"name":"e2e-alpha"}' "Idempotency-Key: $KEY"
expect_status 201 "create"
ID="$(json_field id)"
[ -n "$ID" ] || fail "create: no id in body"
request POST /resources "$EDITOR" '{"name":"e2e-alpha"}' "Idempotency-Key: $KEY"
expect_status 201 "replay"
[ "$(json_field id)" = "$ID" ] || fail "replay returned a different resource"

echo "[e2e] same key, different body -> 422"
request POST /resources "$EDITOR" '{"name":"e2e-beta"}' "Idempotency-Key: $KEY"
expect_status 422 "key reuse with different body"
expect_code VALIDATION.FAILED "key reuse with different body"

echo "[e2e] viewer cannot replay another principal's key -> 403"
request POST /resources "$VIEWER" '{"name":"e2e-alpha"}' "Idempotency-Key: $KEY"
expect_status 403 "viewer replay"
expect_code AUTHZ.DENIED "viewer replay"

echo "[e2e] list contains the created resource exactly once"
request GET "/resources?page=1&page_size=100" "$VIEWER"
expect_status 200 "list"
[ "$(grep -o "\"id\":\"$ID\"" "$BODY_FILE" | wc -l | tr -d ' ')" = 1 ] || fail "list: expected $ID once"

echo "[e2e] delete -> 204, then 404"
request DELETE "/resources/$ID" "$EDITOR"
expect_status 204 "delete"
request GET "/resources/$ID" "$EDITOR"
expect_status 404 "get after delete"

echo "[e2e] ALL E2E CHECKS PASSED"
