#!/usr/bin/env bash
set -euo pipefail
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${TEST_DIR}/../.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/tests/makefile-linter/harness.sh"

SCRIPT="$ROOT/.github/scripts/run-remote-pipeline.sh"
FIXTURE="$TEST_DIR/fixtures"
mkdir -p "$FIXTURE"

assert_eq "1" "$(test -f "$SCRIPT" && echo 1 || echo 0)" "helper script exists"

mock_curl() {
  local http_code="$1"
  local body_file="$2"
  cat >"$FIXTURE/curl" <<EOF
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ "\$#" -gt 0 ]; do
  case "\$1" in
    -o) out="\$2"; shift 2 ;;
    -w) shift 2 ;;
    *) shift ;;
  esac
done
cp "$body_file" "\$out"
printf '%s' "$http_code"
EOF
  chmod +x "$FIXTURE/curl"
}

good_script="$FIXTURE/good.sh"
cat >"$good_script" <<'EOF'
#!/usr/bin/env bash
echo "pipeline-ok"
EOF

html_429="$FIXTURE/github-429.html"
cat >"$html_429" <<'EOF'
<!DOCTYPE html>
<!--
Hello
-->
<html>
<head><title>Whoa there!</title></head>
<body>rate limit</body>
</html>
EOF

mock_curl "200" "$good_script"
out="$(CURL_CMD="$FIXTURE/curl" bash "$SCRIPT" "https://example.test/pipeline.sh")"
assert_eq "pipeline-ok" "$out" "runs a real pipeline script on HTTP 200"

mock_curl "429" "$html_429"
set +e
err="$(CURL_CMD="$FIXTURE/curl" bash "$SCRIPT" "https://example.test/pipeline.sh" 2>&1)"
rc=$?
set -e
assert_eq "1" "$rc" "HTTP 429 exits 1"
assert_contains "$err" "::error::CICD pipeline download failed (HTTP 429). GitHub is rate-limited or down. This is not a lint failure; retry later." "HTTP 429 emits annotation"
assert_contains "$err" "Pipeline URL: https://example.test/pipeline.sh" "HTTP 429 logs pipeline URL"

mock_curl "200" "$html_429"
set +e
err="$(CURL_CMD="$FIXTURE/curl" bash "$SCRIPT" "https://example.test/pipeline.sh" 2>&1)"
rc=$?
set -e
assert_eq "1" "$rc" "HTML body on HTTP 200 exits 1"
assert_contains "$err" "::error::GitHub returned HTML instead of pipeline.sh. Likely rate limiting. This is not a lint failure; retry later." "HTML body emits annotation"

empty="$FIXTURE/empty.sh"
: >"$empty"
mock_curl "200" "$empty"
set +e
err="$(CURL_CMD="$FIXTURE/curl" bash "$SCRIPT" "https://example.test/pipeline.sh" 2>&1)"
rc=$?
set -e
assert_eq "1" "$rc" "empty body exits 1"
assert_contains "$err" "::error::CICD pipeline download was empty. GitHub is unavailable. This is not a lint failure; retry later." "empty body emits annotation"

failing_curl="$FIXTURE/curl-fail"
cat >"$failing_curl" <<'EOF'
#!/usr/bin/env bash
exit 7
EOF
chmod +x "$failing_curl"
set +e
err="$(CURL_CMD="$failing_curl" bash "$SCRIPT" "https://example.test/pipeline.sh" 2>&1)"
rc=$?
set -e
assert_eq "1" "$rc" "curl transport failure exits 1"
assert_contains "$err" "::error::Could not reach GitHub to download the CICD pipeline. This is not a lint failure; retry later." "transport failure emits annotation"

finish
