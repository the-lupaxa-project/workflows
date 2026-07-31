#!/usr/bin/env bash
set -euo pipefail

# Environment (consumed; some wired in later tasks):
#   INCLUDE_FILES, EXCLUDE_FILES, REPORT_ONLY, SHOW_ERRORS, SHOW_SKIPPED,
#   NO_COLOR, CHECK_CONVENTIONS, CHECKMAKE_BIN, ROOT_DIR

makefile_linter_discover() {
  local root="${ROOT_DIR:-$PWD}"
  local include="${INCLUDE_FILES:-}"
  local exclude="${EXCLUDE_FILES:-}"
  local -a discovered=()
  local path rel base

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
  done < <(
    find "$root" -type f \( \
      -name 'Makefile' -o -name 'makefile' -o -name 'GNUmakefile' -o \
      -name '*.mk' -o -name '*.make' \
    \) ! -path '*/.makefiles/*' ! -path '*/lupaxa-dotgithub/*' ! -path '*/.git/*' -print0
  )

  local -a filtered=()
  local pattern item keep
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
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -f "${script_dir}/makefile-conventions.sh" ]; then
    # shellcheck disable=SC1091
    source "${script_dir}/makefile-conventions.sh"
    makefile_conventions_check "$file"
    return $?
  fi
  return 0
}

makefile_linter_conventions_enabled() {
  case "${CHECK_CONVENTIONS:-}" in
    true|True|1) return 0 ;;
    *) return 1 ;;
  esac
}

makefile_linter_main() {
  local root="${ROOT_DIR:-$PWD}"
  local include="${INCLUDE_FILES:-}"
  local -a files=()
  local file failures=0

  while IFS= read -r file; do
    [ -n "$file" ] && files+=("$file")
  done < <(makefile_linter_discover)

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
