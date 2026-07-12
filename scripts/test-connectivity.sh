#!/usr/bin/env bash
set -euo pipefail

run_test() {
  local source_container="$1"
  local target_url="$2"
  local expected="$3"

  local actual

  if docker exec "$source_container" python -c "import urllib.request; urllib.request.urlopen('${target_url}', timeout=3).status" >/dev/null 2>&1; then
    actual="allowed"
  else
    actual="blocked"
  fi

  echo "${source_container} -> ${target_url}: expected=${expected}, actual=${actual}"

  if [[ "$actual" == "$expected" ]]; then
    echo "PASS"
  else
    echo "FAIL"
    return 1
  fi

  echo
}

echo "Running NeoBank network connectivity checks..."
echo

run_test neobank-corp-agent http://core-svc:8000/health allowed
run_test neobank-core-svc http://pci-svc:8000/health allowed
run_test neobank-corp-agent http://pci-svc:8000/health blocked
run_test neobank-dmz-gw http://pci-svc:8000/health blocked

echo "All connectivity checks passed."
