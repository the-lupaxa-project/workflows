#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$(dirname "$0")/harness.sh"
export LIBRARY_MODE=1
source "$ROOT/.github/scripts/makefile-conventions.sh"

profile="$(makefile_conventions_profile "$ROOT/tests/makefile-linter/fixtures/wrapper/Makefile")"
assert_eq "wrapper" "$profile" "detects wrapper"

profile="$(makefile_conventions_profile "$ROOT/tests/makefile-linter/fixtures/skill/skills/demo.mk")"
assert_eq "skill" "$profile" "detects skill"

profile="$(makefile_conventions_profile "$ROOT/tests/makefile-linter/fixtures/template/skills/_template.language.mk")"
assert_eq "template" "$profile" "detects template"

profile="$(makefile_conventions_profile "$ROOT/tests/makefile-linter/fixtures/generic/Makefile")"
assert_eq "generic" "$profile" "detects generic"

profile="$(makefile_conventions_profile "$ROOT/tests/makefile-linter/fixtures/library/Makefile")"
assert_eq "library" "$profile" "detects library before skill heuristics"

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/wrapper/Makefile" 2>&1)"
rc=$?
set -e
assert_eq "0" "$rc" "good wrapper passes"

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/wrapper-bad/Makefile" 2>&1)"
rc=$?
set -e
assert_eq "1" "$rc" "bad wrapper fails"
assert_contains_msg() { printf '%s' "$1" | grep -q -- "$2"; }
if assert_contains_msg "$out" "PHONY"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: expected PHONY finding"; fi

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/skill/skills/demo.mk" 2>&1)"
rc=$?
set -e
assert_eq "0" "$rc" "good skill passes"

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/skill-continuation/skills/demo.mk" 2>&1)"
rc=$?
set -e
assert_eq "0" "$rc" "continued PHONY declaration passes without backslash target"
if printf '%s' "$out" | grep -Fq "public target '\\'"; then
  FAIL=$((FAIL+1))
  echo "FAIL: continued PHONY emitted a backslash target"
else
  PASS=$((PASS+1))
fi

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/library/Makefile" 2>&1)"
rc=$?
set -e
assert_eq "0" "$rc" "library wrapper delegates lifecycle through included template"

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/versioning/skills/versioning.mk" 2>&1)"
rc=$?
set -e
assert_eq "0" "$rc" "versioning accepts doctor-id and unprefixed lifecycle targets"

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/skill-bad/skills/demo.mk" 2>&1)"
rc=$?
set -e
assert_eq "1" "$rc" "unprefixed skill target fails"

set +e
out="$(makefile_conventions_check "$ROOT/tests/makefile-linter/fixtures/template/skills/_template.language.mk" 2>&1)"
rc=$?
set -e
assert_eq "0" "$rc" "template relaxed pass"

finish
