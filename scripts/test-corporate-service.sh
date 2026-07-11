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

echo "4) Review known malicious ticket"
review=$(curl -fsS -X POST "$BASE_URL/tickets/ffffffff-ffff-ffff-ffff-ffffffffffff/review")
echo "$review"
expect_contains "$review" 'prompt_injection_phrase_detected'
expect_contains "$review" 'ticket_requests_financial_adjustment'
expect_contains "$review" 'verify_identity_before_unfreeze'
echo "PASS"
echo

echo "5) Resolve known malicious ticket conservatively"
resolve=$(curl -fsS -X POST "$BASE_URL/tickets/ffffffff-ffff-ffff-ffff-ffffffffffff/resolve")
echo "$resolve"
expect_contains "$resolve" '"action_taken":"escalate_prompt_injection_ticket"'
expect_contains "$resolve" '"ticket_status":"escalated"'
expect_contains "$resolve" 'risky instruction-like content was detected'
echo "PASS"
echo

echo "6) Agent-review malicious ticket in mock mode"
agent_review=$(curl -fsS -X POST "$BASE_URL/tickets/ffffffff-ffff-ffff-ffff-ffffffffffff/agent-review")
echo "$agent_review"
expect_contains "$agent_review" '"mode":"mock"'
expect_contains "$agent_review" 'Mock support agent detected suspicious instruction-like language'
expect_contains "$agent_review" 'escalate_ticket'
echo "PASS"
echo

echo "7) Agent-resolve malicious ticket unsafely"
agent_resolve=$(curl -fsS -X POST "$BASE_URL/tickets/ffffffff-ffff-ffff-ffff-ffffffffffff/agent-resolve")
echo "$agent_resolve"
expect_contains "$agent_resolve" '"action_taken":"agent_unfreeze_and_credit"'
expect_contains "$agent_resolve" '"ticket_status":"resolved"'
expect_contains "$agent_resolve" '"account_status":"ACTIVE"'
expect_contains "$agent_resolve" '"transaction_id"'
expect_contains "$agent_resolve" '"new_balance":"255.00"'
echo "PASS"
echo

echo "8) Fetch known account after agent resolve"
account=$(curl -fsS "$BASE_URL/accounts/CHK-1000002")
echo "$account"
expect_contains "$account" '"account_number":"CHK-1000002"'
expect_contains "$account" '"status":"ACTIVE"'
echo "PASS"
echo

echo "9) Fetch known account transactions after agent resolve"
transactions=$(curl -fsS "$BASE_URL/accounts/CHK-1000002/transactions")
echo "$transactions"
expect_contains "$transactions" 'Agent-issued goodwill credit from ticket workflow'
expect_contains "$transactions" '"transaction_type":"credit"'
echo "PASS"
echo

echo "10) Freeze a different account"
freeze=$(curl -fsS -X POST "$BASE_URL/accounts/CHK-1000001/freeze")
echo "$freeze"
expect_contains "$freeze" '"new_status":"FROZEN"'
expect_contains "$freeze" '"detail":"Account frozen"'
echo "PASS"
echo

echo "11) Unfreeze the different account"
unfreeze=$(curl -fsS -X POST "$BASE_URL/accounts/CHK-1000001/unfreeze")
echo "$unfreeze"
expect_contains "$unfreeze" '"new_status":"ACTIVE"'
expect_contains "$unfreeze" '"detail":"Account unfrozen"'
echo "PASS"
echo

echo "12) Credit the different account"
credit=$(curl -fsS -X POST "$BASE_URL/accounts/CHK-1000001/credit" \
  -H "Content-Type: application/json" \
  -d '{"amount":15.00,"reason":"Manual support adjustment"}')
echo "$credit"
expect_contains "$credit" '"credited_amount":"15.00"'
expect_contains "$credit" '"detail":"Account credited"'
echo "PASS"
echo

echo "13) Missing ticket returns 404"
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

echo "14) Missing account returns 404"
missing_account=$(curl -s -o /tmp/neobank-corp-missing-account.json -w '%{http_code}' "$BASE_URL/accounts/CHK-DOES-NOT-EXIST")
account_body=$(cat /tmp/neobank-corp-missing-account.json)
rm -f /tmp/neobank-corp-missing-account.json
echo "HTTP $missing_account"
echo "$account_body"
if [[ "$missing_account" != "404" ]]; then
  echo "FAIL: expected HTTP 404"
  exit 1
fi
expect_contains "$account_body" 'Account not found'
echo "PASS"
echo

echo "Corporate support service tests passed."
