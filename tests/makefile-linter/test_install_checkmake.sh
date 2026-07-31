#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
set -euo pipefail
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${TEST_DIR}/../.." && pwd)"
# shellcheck source=harness.sh
source "${TEST_DIR}/harness.sh"
export LIBRARY_MODE=1
# shellcheck source=../../.github/scripts/install-checkmake.sh
source "$ROOT/.github/scripts/install-checkmake.sh"

good="$(mktemp)"
echo hello >"$good"
sum="$(sha256sum "$good" | awk '{print $1}')"
if checkmake_verify_file "$good" "$sum"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL verify good"; fi
if checkmake_verify_file "$good" "deadbeef"; then FAIL=$((FAIL+1)); echo "FAIL expected mismatch"; else PASS=$((PASS+1)); fi
rm -f "$good"
finish
