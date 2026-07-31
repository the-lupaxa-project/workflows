#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=harness.sh
source "$(dirname "$0")/harness.sh"
SCRIPT="$ROOT/.github/scripts/makefile-linter.sh"

# Source discover helpers if the script supports LIBRARY_MODE=1
export LIBRARY_MODE=1
# shellcheck disable=SC1090
source "$SCRIPT"

FIXTURE="$ROOT/tests/makefile-linter/fixtures/generic"
out="$(ROOT_DIR="$FIXTURE" makefile_linter_discover)"
assert_contains "$out" "Makefile" "discovers root Makefile"

FIXTURE="$ROOT/tests/makefile-linter/fixtures/nested"
out="$(ROOT_DIR="$FIXTURE" makefile_linter_discover)"
assert_contains "$out" "subdir/build.mk" "discovers nested *.mk"

FIXTURE="$ROOT/tests/makefile-linter/fixtures/with-makefiles-dir"
out="$(ROOT_DIR="$FIXTURE" makefile_linter_discover)"
assert_contains "$out" "Makefile" "keeps wrapper Makefile"
assert_not_contains "$out" ".makefiles/skills/python.mk" "excludes .makefiles"

out="$(ROOT_DIR="$ROOT/tests/makefile-linter/fixtures/generic" INCLUDE_FILES='.*\.mk$' makefile_linter_discover || true)"
assert_eq "" "$out" "include-only-mk against makefile-only fixture yields empty"

set +e
ROOT_DIR="$ROOT/tests/makefile-linter/fixtures/generic" INCLUDE_FILES='.*\.mk$' CHECK_CONVENTIONS=false CHECKMAKE_BIN=true \
  bash "$SCRIPT"
rc=$?
set -e
assert_eq "2" "$rc" "explicit include with zero matches exits 2"

set +e
ROOT_DIR="$(mktemp -d)" CHECK_CONVENTIONS=false CHECKMAKE_BIN=true bash "$SCRIPT"
rc=$?
set -e
assert_eq "0" "$rc" "empty discovery succeeds"

finish
