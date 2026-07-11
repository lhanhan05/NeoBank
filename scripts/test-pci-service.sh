#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"

expect_contains() {
  local response="$1"
  local expected="$2"
  if [[ "$response" != *"$expected"* ]]; then
    echo "FAIL: expected response to contain: $expected"
    echo "Actual: $response"
    exit 1
  fi
}

echo "Testing PCI service at $BASE_URL"

echo "1) Health check"
health=$(curl -fsS "$BASE_URL/health")
echo "$health"
expect_contains "$health" '"status":"ok"'
echo "PASS"
echo

echo "2) Active card approval"
active=$(curl -fsS -X POST "$BASE_URL/authorize" \
  -H "Content-Type: application/json" \
  -d '{"token":"tok_luke_4242","merchant":"Blue Bottle Coffee","amount":24.58}')
echo "$active"
expect_contains "$active" '"approved":true'
expect_contains "$active" '"card_status":"ACTIVE"'
echo "PASS"
echo

echo "3) Expired card decline"
expired=$(curl -fsS -X POST "$BASE_URL/authorize" \
  -H "Content-Type: application/json" \
  -d '{"token":"tok_jane_1881","merchant":"Online Subscription Co","amount":12.99}')
echo "$expired"
expect_contains "$expired" '"approved":false'
expect_contains "$expired" '"card_status":"EXPIRED"'
echo "PASS"
echo

echo "4) Frozen card decline"
frozen=$(curl -fsS -X POST "$BASE_URL/authorize" \
  -H "Content-Type: application/json" \
  -d '{"token":"tok_bob_3005","merchant":"Electronics Depot","amount":199.99}')
echo "$frozen"
expect_contains "$frozen" '"approved":false'
expect_contains "$frozen" '"card_status":"FROZEN"'
echo "PASS"
echo

echo "5) Unknown token decline"
unknown=$(curl -fsS -X POST "$BASE_URL/authorize" \
  -H "Content-Type: application/json" \
  -d '{"token":"tok_does_not_exist","merchant":"Test Merchant","amount":5.00}')
echo "$unknown"
expect_contains "$unknown" '"approved":false'
expect_contains "$unknown" 'token was not found'
echo "PASS"
echo

echo "PCI service tests passed."
