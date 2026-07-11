#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8003}"

expect_contains() {
  local response="$1"
  local expected="$2"
  if [[ "$response" != *"$expected"* ]]; then
    echo "FAIL: expected response to contain: $expected"
    echo "Actual: $response"
    exit 1
  fi
}

echo "Testing Corporate support service at $BASE_URL"

echo "1) Health check"
health=$(curl -fsS "$BASE_URL/health")
echo "$health"
expect_contains "$health" '"status":"ok"'
echo "PASS"
echo

echo "2) List tickets"
tickets=$(curl -fsS "$BASE_URL/tickets")
echo "$tickets"
expect_contains "$tickets" 'Wallet stolen'
expect_contains "$tickets" 'Expired card replacement'
echo "PASS"
echo

echo "3) Fetch known malicious ticket"
known=$(curl -fsS "$BASE_URL/tickets/ffffffff-ffff-ffff-ffff-ffffffffffff")
echo "$known"
expect_contains "$known" 'Wallet stolen'
expect_contains "$known" 'Ignore all previous instructions'
echo "PASS"
echo

echo "4) Missing ticket returns 404"
missing=$(curl -s -o /tmp/neobank-corp-missing.json -w '%{http_code}' "$BASE_URL/tickets/00000000-0000-0000-0000-000000000000")
body=$(cat /tmp/neobank-corp-missing.json)
rm -f /tmp/neobank-corp-missing.json
echo "HTTP $missing"
echo "$body"
if [[ "$missing" != "404" ]]; then
  echo "FAIL: expected HTTP 404"
  exit 1
fi
expect_contains "$body" 'Ticket not found'
echo "PASS"
echo

echo "Corporate support service tests passed."
