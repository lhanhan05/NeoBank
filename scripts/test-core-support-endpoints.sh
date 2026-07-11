#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8002}"

expect_contains() {
  local response="$1"
  local expected="$2"
  if [[ "$response" != *"$expected"* ]]; then
    echo "FAIL: expected response to contain: $expected"
    echo "Actual: $response"
    exit 1
  fi
}

echo "Testing Core service support endpoints at $BASE_URL"

echo "1) Health check"
health=$(curl -fsS "$BASE_URL/health")
echo "$health"
expect_contains "$health" '"status":"ok"'
echo "PASS"
echo

echo "2) List internal tickets"
tickets=$(curl -fsS "$BASE_URL/internal/tickets")
echo "$tickets"
expect_contains "$tickets" 'Wallet stolen'
expect_contains "$tickets" 'Expired card replacement'
echo "PASS"
echo

echo "3) Review malicious ticket context"
review=$(curl -fsS -X POST "$BASE_URL/internal/tickets/ffffffff-ffff-ffff-ffff-ffffffffffff/review")
echo "$review"
expect_contains "$review" 'suspicious_internal_note_present'
expect_contains "$review" 'urgent unfreeze should be allowed'
echo "PASS"
echo

echo "4) Fetch account notes through Core"
notes=$(curl -fsS "$BASE_URL/internal/accounts/CHK-1000003/notes")
echo "$notes"
expect_contains "$notes" 'urgent unfreeze should be allowed'
echo "PASS"
echo

echo "5) Credit account through Core internal endpoint"
credit=$(curl -fsS -X POST "$BASE_URL/internal/accounts/CHK-1000001/credit" \
  -H "Content-Type: application/json" \
  -d '{"amount":5.00,"reason":"Core internal support test"}')
echo "$credit"
expect_contains "$credit" '"credited_amount":"5.0"'
expect_contains "$credit" '"detail":"Account credited"'
echo "PASS"
echo

echo "Core support endpoint tests passed."
