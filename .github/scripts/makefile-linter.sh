#!/usr/bin/env bash
set -euo pipefail

# Environment (consumed; some wired in later tasks):
#   INCLUDE_FILES, EXCLUDE_FILES, REPORT_ONLY, SHOW_ERRORS, SHOW_SKIPPED,
#   NO_COLOR, CHECK_CONVENTIONS, CHECKMAKE_BIN, ROOT_DIR

makefile_linter_normalize_root() {
  local root="$1"
  while [ "$root" != "/" ] && [ "${root: -1}" = "/" ]; do
    root="${root%/}"
  done
  printf '%s' "$root"
}

makefile_linter_validate_root() {
  local root
  root="$(makefile_linter_normalize_root "$1")"

  if [ ! -d "$root" ]; then
    echo "ROOT_DIR is not a directory: ${root}" >&2
    return 1
  fi
  if [ ! -r "$root" ] || [ ! -x "$root" ]; then
    echo "ROOT_DIR is not accessible: ${root}" >&2
    return 1
  fi
  if ! find "$root" -mindepth 0 -maxdepth 0 >/dev/null 2>&1; then
    echo "Failed to scan ROOT_DIR: ${root}" >&2
    return 1
  fi
  return 0
}

makefile_linter_discover() {
  local root
  root="$(makefile_linter_normalize_root "${ROOT_DIR:-$PWD}")"
  local include="${INCLUDE_FILES:-}"
  local exclude="${EXCLUDE_FILES:-}"
  local -a discovered=()
  local path rel base tmp find_rc=0

  if ! makefile_linter_validate_root "$root"; then
    return 1
  fi

  tmp="$(mktemp)"
  find "$root" -type f \( \
    -name 'Makefile' -o -name 'makefile' -o -name 'GNUmakefile' -o \
    -name '*.mk' -o -name '*.make' \
  \) ! -path '*/.makefiles/*' ! -path '*/lupaxa-dotgithub/*' ! -path '*/.git/*' \
    -print0 >"$tmp" || find_rc=$?
  if [ "$find_rc" -ne 0 ]; then
    rm -f "$tmp"
    echo "Failed to scan ROOT_DIR: ${root}" >&2
    return 1
  fi

  while IFS= read -r -d '' path; do
    rel="${path#"${root}/"}"
    if [ "$rel" = "$path" ] && [ "$path" = "$root" ]; then
      continue
    fi
    base="$(basename "$path")"
    case "$base" in
      Makefile|makefile|GNUmakefile) ;;
      *.mk|*.make) ;;
      *) continue ;;
    esac
    case "$path" in
      */.makefiles/*|*/lupaxa-dotgithub/*|*/.git/*) continue ;;
    esac
    discovered+=("$rel")
  done <"$tmp"
  rm -f "$tmp"

  local -a filtered=()
  local pattern keep
  local IFS=','

  for rel in "${discovered[@]}"; do
    keep=1

    if [ -n "$include" ]; then
      keep=0
      for pattern in $include; do
        if [[ "$rel" =~ $pattern ]]; then
          keep=1
          break
        fi
      done
      [ "$keep" -eq 1 ] || continue
    fi

    if [ -n "$exclude" ]; then
      for pattern in $exclude; do
        if [[ "$rel" =~ $pattern ]]; then
          keep=0
          break
        fi
      done
    fi

    [ "$keep" -eq 1 ] && filtered+=("$rel")
  done

  if [ "${#filtered[@]}" -eq 0 ]; then
    return 0
  fi

  printf '%s\n' "${filtered[@]}" | sort -u
}

makefile_linter_run_checkmake() {
  local file="$1"
  local bin="${CHECKMAKE_BIN:-checkmake}"

  if [ "$bin" = "true" ]; then
    return 0
  fi
  if [ -z "$bin" ] || [ "$bin" = "checkmake" ]; then
    checkmake "$file"
    return $?
  fi
  "$bin" "$file"
}

makefile_linter_run_conventions() {
  local file="$1"
  local script_dir conventions_script

  if [ -n "${CONVENTIONS_SCRIPT:-}" ]; then
    # shellcheck disable=SC1090
    source "$CONVENTIONS_SCRIPT"
    makefile_conventions_check "$file"
    return $?
  fi

  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  conventions_script="${script_dir}/makefile-conventions.sh"
  if [ ! -f "$conventions_script" ]; then
    echo "Convention checker not found: ${conventions_script}" >&2
    return 1
  fi

  if [ "${LIBRARY_MODE:-}" = "1" ]; then
    # shellcheck disable=SC1090
    source "$conventions_script"
    makefile_conventions_check "$file"
    return $?
  fi

  bash "$conventions_script" "$file"
}

makefile_linter_conventions_enabled() {
  case "${CHECK_CONVENTIONS:-true}" in
    false|False|0) return 1 ;;
    *) return 0 ;;
  esac
}

makefile_linter_main() {
  local root
  root="$(makefile_linter_normalize_root "${ROOT_DIR:-$PWD}")"
  local include="${INCLUDE_FILES:-}"
  local -a files=()
  local file failures=0

  local discover_out discover_rc=0

  if ! makefile_linter_validate_root "$root"; then
    exit 1
  fi

  discover_out="$(makefile_linter_discover)" || discover_rc=$?
  if [ "$discover_rc" -ne 0 ]; then
    exit 1
  fi

  while IFS= read -r file; do
    [ -n "$file" ] && files+=("$file")
  done <<< "$discover_out"

  if [ "${#files[@]}" -eq 0 ]; then
    if [ -n "$include" ]; then
      echo "No Makefile files matched INCLUDE_FILES under ${root}." >&2
      exit 2
    fi
    echo "No Makefile files to validate."
    exit 0
  fi

  for file in "${files[@]}"; do
    local fpath="${root}/${file}"
    if ! makefile_linter_run_checkmake "$fpath"; then
      failures=$((failures + 1))
    fi
    if makefile_linter_conventions_enabled; then
      if ! makefile_linter_run_conventions "$fpath"; then
        failures=$((failures + 1))
      fi
    fi
  done

  if [ "$failures" -gt 0 ]; then
    case "${REPORT_ONLY:-}" in
      true|True|1) exit 0 ;;
      *) exit 1 ;;
    esac
  fi
  exit 0
}

if [ "${LIBRARY_MODE:-}" = "1" ] && [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return 0 2>/dev/null || exit 0
fi

makefile_linter_main "$@"
