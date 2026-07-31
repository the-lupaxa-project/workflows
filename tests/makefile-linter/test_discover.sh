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

FIXTURE="$ROOT/tests/makefile-linter/fixtures/with-dotgithub"
out="$(ROOT_DIR="$FIXTURE" makefile_linter_discover)"
assert_contains "$out" "Makefile" "keeps root Makefile in dotgithub fixture"
assert_not_contains "$out" "lupaxa-dotgithub/hidden/Makefile" "excludes lupaxa-dotgithub paths"

FIXTURE="$ROOT/tests/makefile-linter/fixtures/generic"
out="$(ROOT_DIR="$FIXTURE" EXCLUDE_FILES='^Makefile$' makefile_linter_discover)"
assert_eq "" "$out" "EXCLUDE_FILES removes matching paths"

FIXTURE="$ROOT/tests/makefile-linter/fixtures/aliases"
out="$(ROOT_DIR="$FIXTURE" makefile_linter_discover)"
assert_contains "$out" "makefile" "discovers lowercase makefile"
assert_contains "$out" "GNUmakefile" "discovers GNUmakefile"
assert_contains "$out" "build.make" "discovers *.make files"

unset CHECK_CONVENTIONS
if makefile_linter_conventions_enabled; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
  echo "FAIL: conventions enabled by default when CHECK_CONVENTIONS unset" >&2
fi

set +e
out="$(ROOT_DIR="/nonexistent/path/for/makefile-linter" makefile_linter_discover 2>/dev/null)"
rc=$?
set -e
assert_eq "1" "$rc" "invalid ROOT_DIR fails discovery instead of empty success"

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

STUB_DIR="$(mktemp -d)"
trap 'rm -rf "$STUB_DIR"' EXIT
cat > "$STUB_DIR/fail-checkmake.sh" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$STUB_DIR/fail-checkmake.sh"

cat > "$STUB_DIR/conventions-stub.sh" <<EOF
#!/usr/bin/env bash
makefile_conventions_check() {
  echo ran > "$STUB_DIR/conventions-ran"
}
EOF

set +e
ROOT_DIR="$ROOT/tests/makefile-linter/fixtures/generic" CHECKMAKE_BIN="$STUB_DIR/fail-checkmake.sh" \
  bash "$SCRIPT"
rc=$?
set -e
assert_eq "1" "$rc" "failing checkmake exits 1 without REPORT_ONLY"

set +e
ROOT_DIR="$ROOT/tests/makefile-linter/fixtures/generic" CHECKMAKE_BIN="$STUB_DIR/fail-checkmake.sh" \
  REPORT_ONLY=true bash "$SCRIPT"
rc=$?
set -e
assert_eq "0" "$rc" "REPORT_ONLY=true exits 0 despite failing checkmake"

rm -f "$STUB_DIR/conventions-ran"
set +e
ROOT_DIR="$ROOT/tests/makefile-linter/fixtures/generic" CHECKMAKE_BIN=true \
  CONVENTIONS_SCRIPT="$STUB_DIR/conventions-stub.sh" bash "$SCRIPT"
rc=$?
set -e
assert_eq "0" "$rc" "orchestrator succeeds with default conventions enabled"
assert_eq "ran" "$(cat "$STUB_DIR/conventions-ran" 2>/dev/null || true)" "default conventions run when CHECK_CONVENTIONS unset"

finish
