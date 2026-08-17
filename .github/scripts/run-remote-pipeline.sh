#!/usr/bin/env bash
# Download a CICD Toolbox pipeline.sh and run it.
# Fail with a GitHub Actions annotation when GitHub returns HTML / 429 / empty.
set -euo pipefail

usage() {
  echo "Usage: $0 <pipeline-url>" >&2
  exit 2
}

[ "$#" -eq 1 ] || usage
url="$1"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl_cmd="${CURL_CMD:-curl}"
http_code=""
fail_download() {
  local annotation="$1"
  echo "::error::${annotation}"
  echo "Pipeline URL: ${url}" >&2
  exit 1
}

if ! http_code="$("${curl_cmd}" -sS -L --retry 2 --retry-delay 3 --max-time 30 -o "$tmp" -w '%{http_code}' "$url")"; then
  fail_download "Could not reach GitHub to download the CICD pipeline. This is not a lint failure; retry later."
fi

if [ "$http_code" != "200" ]; then
  fail_download "CICD pipeline download failed (HTTP ${http_code}). GitHub is rate-limited or down. This is not a lint failure; retry later."
fi

if [ ! -s "$tmp" ]; then
  fail_download "CICD pipeline download was empty. GitHub is unavailable. This is not a lint failure; retry later."
fi

if head -n 8 "$tmp" | grep -qiE '<!DOCTYPE|<html'; then
  fail_download "GitHub returned HTML instead of pipeline.sh. Likely rate limiting. This is not a lint failure; retry later."
fi

bash "$tmp"
