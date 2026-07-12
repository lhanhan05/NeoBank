#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
RESET_EXPLOIT_STATE="${RESET_EXPLOIT_STATE:-true}"

expect_contains() {
  local response="$1"
  local expected="$2"
  if [[ "$response" != *"$expected"* ]]; then
    echo "FAIL: expected response to contain: $expected"
    echo "Actual: $response"
    exit 1
  fi
}

echo "Testing DMZ gateway at $BASE_URL"

if [[ "$RESET_EXPLOIT_STATE" == "true" ]]; then
  echo "0) Reset exploit baseline so frozen-card coverage is deterministic"
  ./scripts/reset-exploit-state.sh >/dev/null
  echo "PASS"
  echo
fi

echo "1) Health check"
health=$(curl -fsS "$BASE_URL/health")
echo "$health"
expect_contains "$health" '"status":"ok"'
echo "PASS"
echo

echo "2) Approved public-edge flow"
active=$(curl -fsS -X POST "$BASE_URL/api/v1/auth-payment" \
  -H "Content-Type: application/json" \
  -d '{"account_number":"CHK-1000001","merchant":"Blue Bottle Coffee","amount":24.58}')
echo "$active"
expect_contains "$active" '"approved":true'
expect_contains "$active" '"account_status":"ACTIVE"'
expect_contains "$active" '"card_status":"ACTIVE"'
echo "PASS"
echo

echo "3) Expired card public-edge decline"
expired=$(curl -fsS -X POST "$BASE_URL/api/v1/auth-payment" \
  -H "Content-Type: application/json" \
  -d '{"account_number":"CHK-1000002","merchant":"Online Subscription Co","amount":12.99}')
echo "$expired"
expect_contains "$expired" '"approved":false'
expect_contains "$expired" '"card_status":"EXPIRED"'
echo "PASS"
echo

echo "4) Frozen account public-edge decline before PCI call"
frozen=$(curl -fsS -X POST "$BASE_URL/api/v1/auth-payment" \
  -H "Content-Type: application/json" \
  -d '{"account_number":"CHK-1000003","merchant":"Electronics Depot","amount":199.99}')
echo "$frozen"
expect_contains "$frozen" '"approved":false'
expect_contains "$frozen" '"account_status":"FROZEN"'
expect_contains "$frozen" '"card_status":null'
echo "PASS"
echo

echo "5) Missing account public-edge decline"
missing=$(curl -fsS -X POST "$BASE_URL/api/v1/auth-payment" \
  -H "Content-Type: application/json" \
  -d '{"account_number":"CHK-DOES-NOT-EXIST","merchant":"Unknown Merchant","amount":5.00}')
echo "$missing"
expect_contains "$missing" '"approved":false'
expect_contains "$missing" '"reason":"Account not found"'
echo "PASS"
echo

echo "DMZ gateway tests passed."
