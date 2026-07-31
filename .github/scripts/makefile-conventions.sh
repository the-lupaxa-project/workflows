#!/usr/bin/env bash
set -euo pipefail

makefile_conventions_profile() {
  local file="$1"
  local base
  base="$(basename "$file")"

  case "$base" in
    _*.mk)
      printf '%s\n' "template"
      return 0
      ;;
  esac

  if [[ "$file" == */skills/* || "$file" == skills/* ]]; then
    printf '%s\n' "skill"
    return 0
  fi

  if grep -Eq '^[[:space:]]*MAKEFILES_MODE[[:space:]]*[?:+]?=[[:space:]]*library([[:space:]]|$)' "$file"; then
    printf '%s\n' "library"
    return 0
  fi

  if grep -Eq 'MAKEFILES_DIR|MAKEFILES_REPO|^[[:space:]]*SKILLS([[:space:]]|[?:+]?=)|^[[:space:]]*-include[[:space:]].*/skills/' "$file"; then
    printf '%s\n' "wrapper"
    return 0
  fi

  if [[ "$base" == *.mk ]] &&
    grep -Eq 'STATUS_FRAGMENTS|^[[:space:]]*help-[[:alnum:]_.-]+[[:space:]]*:' "$file"; then
    printf '%s\n' "skill"
    return 0
  fi

  printf '%s\n' "generic"
}

makefile_conventions_finding() {
  local file="$1"
  local rule="$2"
  local message="$3"
  printf '%s:%s: %s\n' "$file" "$rule" "$message"
}

makefile_conventions_phony_targets() {
  awk '
    {
      logical = $0
      while (logical ~ /\\[[:space:]]*$/) {
        sub(/\\[[:space:]]*$/, "", logical)
        if ((getline continued) <= 0) {
          break
        }
        logical = logical " " continued
      }
      if (logical ~ /^[[:space:]]*\.PHONY[[:space:]]*:/) {
        sub(/^[[:space:]]*\.PHONY[[:space:]]*:[[:space:]]*/, "", logical)
        print logical
      }
    }
  ' "$1"
}

makefile_conventions_phony_has() {
  local targets="$1"
  local target="$2"
  printf '%s\n' "$targets" | grep -Eq "(^|[[:space:]])${target}([[:space:]]|$)"
}

makefile_conventions_check_wrapper() {
  local file="$1"
  local findings=0
  local phony
  phony="$(makefile_conventions_phony_targets "$file")"

  if ! grep -q 'MAKEFILES_DIR' "$file"; then
    makefile_conventions_finding "$file" "WRAPPER_CONFIG" "missing MAKEFILES_DIR"
    findings=$((findings + 1))
  fi
  if ! grep -Eq 'MAKEFILES_REPO|MAKEFILES_REPO_(SSH|HTTP)' "$file"; then
    makefile_conventions_finding "$file" "WRAPPER_CONFIG" "missing MAKEFILES_REPO configuration"
    findings=$((findings + 1))
  fi
  if ! grep -Eq '^[[:space:]]*-include[[:space:]].*skills/' "$file"; then
    makefile_conventions_finding "$file" "WRAPPER_INCLUDE" "missing -include for skills/"
    findings=$((findings + 1))
  fi

  local target
  for target in init help; do
    if ! makefile_conventions_phony_has "$phony" "$target"; then
      makefile_conventions_finding "$file" "WRAPPER_PHONY" "PHONY must list ${target}"
      findings=$((findings + 1))
    fi
  done
  if grep -Eq '^[[:space:]]*update[[:space:]]*:' "$file" &&
    ! makefile_conventions_phony_has "$phony" "update"; then
    makefile_conventions_finding "$file" "WRAPPER_PHONY" "PHONY must list update"
    findings=$((findings + 1))
  fi

  [ "$findings" -eq 0 ]
}

makefile_conventions_skill_id() {
  local file="$1"
  local base id
  base="$(basename "$file")"

  case "$base" in
    *.mk) id="${base%.mk}" ;;
    *)
      id="$(awk '
        /^[[:space:]]*help-[[:alnum:]_.-]+[[:space:]]*:/ {
          sub(/^[[:space:]]*help-/, "")
          sub(/[[:space:]]*:.*$/, "")
          print
          exit
        }
      ' "$file")"
      ;;
  esac

  printf '%s\n' "$id"
}

makefile_conventions_check_skill() {
  local file="$1"
  local findings=0
  local id phony fragments target doctor_pattern
  id="$(makefile_conventions_skill_id "$file")"

  if [ -z "$id" ]; then
    makefile_conventions_finding "$file" "SKILL_ID" "could not determine skill id"
    return 1
  fi

  if ! grep -Eq "^[[:space:]]*help-${id}[[:space:]]*:" "$file"; then
    makefile_conventions_finding "$file" "SKILL_TARGET" "missing help-${id} target"
    findings=$((findings + 1))
  fi
  doctor_pattern="${id}-doctor|doctor-${id}"
  [ "$id" = "versioning" ] && doctor_pattern="${doctor_pattern}|doctor"
  if ! grep -Eq "^[[:space:]]*(${doctor_pattern})[[:space:]]*:" "$file"; then
    makefile_conventions_finding "$file" "SKILL_TARGET" "missing ${id}-doctor or doctor-${id} target"
    findings=$((findings + 1))
  fi
  if grep -Eq '^[[:space:]]*-?include[[:space:]].*\.mk([[:space:]]|$)' "$file"; then
    makefile_conventions_finding "$file" "SKILL_INCLUDE" "skill files must not include other .mk files"
    findings=$((findings + 1))
  fi

  phony="$(makefile_conventions_phony_targets "$file")"
  fragments="$(awk '
    /^[[:space:]]*STATUS_FRAGMENTS[[:space:]]*\+?=/ {
      sub(/^[^=]*=[[:space:]]*/, "")
      print
    }
  ' "$file")"

  for target in $phony; do
    case "$target" in
      \#*) break ;;
      "help-${id}"|"status-${id}"|"doctor-${id}"|"${id}-"*) continue ;;
    esac
    if [ "$id" = "versioning" ]; then
      case "$target" in
        bump-*|release|doctor|status|version|show-version-flow) continue ;;
      esac
    fi
    if makefile_conventions_phony_has "$fragments" "$target"; then
      continue
    fi
    makefile_conventions_finding "$file" "SKILL_PHONY" "public target '${target}' must use the ${id}- prefix"
    findings=$((findings + 1))
  done

  [ "$findings" -eq 0 ]
}

makefile_conventions_check() {
  local file="$1"
  local profile
  profile="$(makefile_conventions_profile "$file")"

  case "$profile" in
    wrapper) makefile_conventions_check_wrapper "$file" ;;
    skill) makefile_conventions_check_skill "$file" ;;
    library|template|generic) return 0 ;;
  esac
}

makefile_conventions_main() {
  local file
  local failures=0

  if [ "$#" -eq 0 ]; then
    echo "Usage: $0 FILE..." >&2
    return 2
  fi

  for file in "$@"; do
    if ! makefile_conventions_check "$file"; then
      failures=$((failures + 1))
    fi
  done

  [ "$failures" -eq 0 ]
}

# When sourced with LIBRARY_MODE=1 (unit tests), expose helpers only.
if [ "${LIBRARY_MODE:-}" = "1" ] && [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  :
else
  makefile_conventions_main "$@"
fi
