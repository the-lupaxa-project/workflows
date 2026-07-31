#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${TEST_DIR}/../.." && pwd)"
# CI shellcheck runs one file at a time without -x; do not require following.
# shellcheck source=/dev/null
source "${TEST_DIR}/harness.sh"
export LIBRARY_MODE=1
# shellcheck source=/dev/null
source "$ROOT/.github/scripts/install-checkmake.sh"

good="$(mktemp)"
echo hello >"$good"
sum="$(sha256sum "$good" | awk '{print $1}')"
if checkmake_verify_file "$good" "$sum"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL verify good"; fi
if checkmake_verify_file "$good" "deadbeef"; then FAIL=$((FAIL+1)); echo "FAIL expected mismatch"; else PASS=$((PASS+1)); fi
rm -f "$good"
finish
