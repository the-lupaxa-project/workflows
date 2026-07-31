#!/usr/bin/env bash
# install-checkmake.sh — download and verify pinned checkmake
set -euo pipefail

CHECKMAKE_VERSION="${CHECKMAKE_VERSION:-v0.3.2}"
CHECKMAKE_ASSET="${CHECKMAKE_ASSET:-checkmake-v0.3.2.linux.amd64}"
CHECKMAKE_SHA256="${CHECKMAKE_SHA256:-e2effb876913f3ee2caef0ba35f6202c5e8a3cd55a077d8d2b9ce2034257b6af}"
CHECKMAKE_URL="${CHECKMAKE_URL:-https://github.com/checkmake/checkmake/releases/download/${CHECKMAKE_VERSION}/${CHECKMAKE_ASSET}}"

checkmake_verify_file() {
  local file="$1" expected="$2"
  local actual
  actual="$(sha256sum "$file" | awk '{print $1}')"
  [ "$actual" = "$expected" ]
}

install_checkmake() {
  local dest_dir="$1"
  mkdir -p "$dest_dir"
  local tmp
  tmp="$(mktemp)"
  curl -fsSL "$CHECKMAKE_URL" -o "$tmp"
  if ! checkmake_verify_file "$tmp" "$CHECKMAKE_SHA256"; then
    echo "ERROR: checkmake checksum mismatch" >&2
    rm -f "$tmp"
    return 1
  fi
  install -m 0755 "$tmp" "$dest_dir/checkmake"
  rm -f "$tmp"
  printf '%s\n' "$dest_dir/checkmake"
}

if [ "${LIBRARY_MODE:-0}" != "1" ]; then
  install_checkmake "${1:-${RUNNER_TEMP:-/tmp}/checkmake-bin}"
fi
