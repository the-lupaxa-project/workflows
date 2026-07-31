#!/usr/bin/env bash
set -euo pipefail

PASS=0
FAIL=0

assert_eq() {
  local expected="$1" actual="$2" msg="${3:-}"
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: ${msg} expected='${expected}' actual='${actual}'" >&2
  fi
}

assert_contains() {
  local haystack="$1" needle="$2" msg="${3:-}"
  if printf '%s' "$haystack" | grep -Fqx -- "$needle"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: ${msg} missing line '${needle}'" >&2
  fi
}

assert_not_contains() {
  local haystack="$1" needle="$2" msg="${3:-}"
  if printf '%s' "$haystack" | grep -Fqx -- "$needle"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: ${msg} unexpectedly found '${needle}'" >&2
  else
    PASS=$((PASS + 1))
  fi
}

finish() {
  echo "Passed: ${PASS}  Failed: ${FAIL}"
  [ "$FAIL" -eq 0 ]
}
