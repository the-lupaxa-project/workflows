#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
fail=0
for t in "$DIR"/test_*.sh; do
  echo "==> $(basename "$t")"
  bash "$t" || fail=1
done
exit "$fail"
