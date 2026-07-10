#!/usr/bin/env bash
set -euo pipefail

run_test() {
  local source_container="$1"
  local target_host="$2"
  local expected="$3"

  local actual

  if docker exec "$source_container" python -c "import urllib.request; urllib.request.urlopen('http://${target_host}:80', timeout=2).status" >/dev/null 2>&1; then
    actual="allowed"
  else
    actual="blocked"
  fi

  echo "${source_container} -> ${target_host}: expected=${expected}, actual=${actual}"

  if [[ "$actual" == "$expected" ]]; then
    echo "PASS"
  else
    echo "FAIL"
    return 1
  fi

  echo
}

echo "Running NeoBank Phase 1 connectivity checks..."
echo

run_test neobank-corp-agent core-svc allowed
run_test neobank-core-svc pci-svc allowed
run_test neobank-core-svc core-db-probe allowed
run_test neobank-pci-svc pci-db-probe allowed
run_test neobank-corp-agent pci-svc blocked
run_test neobank-dmz-gw pci-svc blocked
run_test neobank-corp-agent core-db-probe blocked

echo "All connectivity checks passed."
