#!/usr/bin/env bash

set -euo pipefail

# --------------------------------------------------------------------------------
# Globals (job buckets)
# --------------------------------------------------------------------------------

success_list=()
failed_list=()
cancelled_list=()
skipped_list=()
timed_out_list=()
other_list=()

# ------------------------------------------------------------------------
# GitHub Actions environment variables (defined at runtime)
# Declared here only to silence ShellCheck warnings (SC2154 etc.)
# ------------------------------------------------------------------------
: "${GITHUB_REPOSITORY:=}"
: "${GITHUB_WORKFLOW:=}"
: "${GITHUB_RUN_NUMBER:=}"
: "${GITHUB_RUN_ATTEMPT:=}"
: "${GITHUB_EVENT_NAME:=}"
: "${GITHUB_ACTOR:=}"
: "${GITHUB_TRIGGERING_ACTOR:=}"
: "${GITHUB_REF_NAME:=}"
: "${GITHUB_SHA:=}"
: "${GITHUB_RUN_ID:=}"
: "${GITHUB_STEP_SUMMARY:=}"
: "${GITHUB_EVENT_PATH:=}"

# --------------------------------------------------------------------------------
# ensure_jq: make sure jq is available (attempt installation if missing)
# --------------------------------------------------------------------------------

ensure_jq()
{
    if command -v jq >/dev/null 2>&1; then
        return 0
    fi

    echo "jq not found, attempting to install..." >&2

    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y >/dev/null 2>&1 || true
        sudo apt-get install -y jq >/dev/null 2>&1 || true
    elif command -v apk >/dev/null 2>&1; then
        sudo apk add --no-cache jq >/dev/null 2>&1 || true
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y jq >/dev/null 2>&1 || true
    fi

    if ! command -v jq >/dev/null 2>&1; then
        echo "ERROR: jq could not be installed or found."
        exit 1
    fi
}

# --------------------------------------------------------------------------------
# fetch_jobs_json: call GitHub API for the current run's jobs (matrix-aware)
# Now with proper HTTP status handling + clearer errors.
# --------------------------------------------------------------------------------

fetch_jobs_json()
{
    if [[ -z "${GITHUB_REPOSITORY:-}" || -z "${GITHUB_RUN_ID:-}" ]]; then
        echo "ERROR: GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API." >&2
        return 1
    fi

    # Prefer GITHUB_TOKEN, fall back to ACTIONS_RUNTIME_TOKEN if needed
    local token="${GITHUB_TOKEN:-${ACTIONS_RUNTIME_TOKEN:-}}"
    if [[ -z "${token}" ]]; then
        echo "ERROR: GITHUB_TOKEN (or ACTIONS_RUNTIME_TOKEN) is not set; cannot call GitHub API." >&2
        return 1
    fi

    local api_url="https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs?per_page=100"

    # Capture body + status in one go
    local response http_status body
    response="$(curl -sS -w $'\nHTTP_STATUS=%{http_code}\n' \
        -H "Authorization: Bearer ${token}" \
        -H "Accept: application/vnd.github+json" \
        "${api_url}")" || {
        echo "ERROR: curl failed when calling GitHub API." >&2
        echo "Raw curl output:" >&2
        echo "${response}" >&2
        return 1
    }

    http_status="$(printf '%s\n' "${response}" | awk -F= '/^HTTP_STATUS=/{print $2}')"
    body="$(printf '%s\n' "${response}" | sed '/^HTTP_STATUS=/d')"

    if [[ "${http_status}" != "200" ]]; then
        echo "ERROR: GitHub API returned HTTP ${http_status}." >&2
        echo "Response body was:" >&2
        echo "${body}" >&2
        return 1
    fi

    printf '%s\n' "${body}"
}

# --------------------------------------------------------------------------------
# parse_jobs: parse JSON input into buckets and print per-job text output
# Supports two shapes:
# 1) GitHub Actions API /jobs response:
#      { "jobs": [ { "name": "...", "conclusion": "success" }, ... ] }
# 2) toJson(needs) mapping:
#      { "job_id": { "result": "success", ... }, ... }
# --------------------------------------------------------------------------------

parse_jobs()
{
    local job_results_json="$1"

    # Quick validation: is this even JSON?
    if ! echo "${job_results_json}" | jq -e . >/dev/null 2>&1; then
        echo "ERROR: job_results_json is not valid JSON. Raw value was:" >&2
        echo "----- BEGIN job_results_json -----" >&2
        echo "${job_results_json}" >&2
        echo "----- END job_results_json -----" >&2
        exit 1
    fi

    local parsed

    # Detect if this looks like the /jobs API shape (has "jobs" top-level key)
    if echo "${job_results_json}" | jq -e 'type == "object" and has("jobs")' >/dev/null 2>&1; then
        parsed=$(echo "${job_results_json}" | jq -r '
            .jobs[]
            | "\(.name) \(.conclusion // "unknown")"
        ') || {
            echo "Failed to parse GitHub jobs API JSON via jq."
            exit 1
        }
    else
        # Probably toJson(needs)
        parsed=$(echo "${job_results_json}" | jq -r '
            to_entries[]
            | "\(.key) \(.value.result)"
        ') || {
            echo "Failed to parse job results JSON via jq."
            exit 1
        }
    fi

    while IFS= read -r line; do
        [[ -z "${line}" ]] && continue

        # Extract result = last word
        local job_name_raw result
        job_name_raw=${line% *}
        result=${line##* }

        # If job name has a slash, keep ONLY the right side ("real" job name)
        local job_name="${job_name_raw##*/ }"

        # Trim leading/trailing whitespace
        job_name="$(echo "$job_name" | sed 's/^ *//;s/ *$//')"

        # Ignore umbrella "Status" jobs by default
        if [[ "${CHECK_JOBS_INCLUDE_STATUS:-0}" != "1" ]]; then
            case "${job_name}" in
                *" Status" | "Status" | *"Status")
                    continue
                    ;;
            esac
        fi

        case "$result" in
            success)
                success_list+=("$job_name")
                ;;
            failure)
                failed_list+=("$job_name")
                ;;
            cancelled)
                cancelled_list+=("$job_name")
                ;;
            skipped)
                skipped_list+=("$job_name")
                ;;
            timed_out)
                timed_out_list+=("$job_name")
                ;;
            *)
                other_list+=("${job_name}:${result}")
                ;;
        esac

    done <<< "$parsed"
}

# --------------------------------------------------------------------------------
# print_sorted_section: helper for the summary
# --------------------------------------------------------------------------------

print_sorted_section()
{
    local title="$1"
    shift
    local arr=("$@")

    (( ${#arr[@]} == 0 )) && return

    echo "### ${title}"
    printf '%s\n' "${arr[@]}" \
        | sort -fV \
        | while IFS= read -r j; do
            [[ -z "${j}" ]] && continue
            echo "- ${j}"
        done
    echo
}

# Returns the ordinal suffix for a given day number ("st", "nd", "rd", "th")
ordinal_suffix()
{
    local day="$1"
    local suf

    if (( day == 1 || day == 21 || day == 31 )); then
        suf="st"
    elif (( day == 2 || day == 22 )); then
        suf="nd"
    elif (( day == 3 || day == 23 )); then
        suf="rd"
    else
        suf="th"
    fi

    echo "<sup>${suf}</sup>"
}

# Build a human-readable timestamp
build_human_timestamp()
{
    local day month_name year time dow suffix
    day="$(date -u +'%d' | sed 's/^0//')"          # 1–31
    dow="$(date -u +'%A')"                         # Monday
    month_name="$(date -u +'%B')"                  # November
    year="$(date -u +'%Y')"                        # 2025
    time="$(date -u +'%H:%M:%S')"                  # 18:03:45
    suffix="$(ordinal_suffix "${day}")"

    echo "${dow} ${day}${suffix} ${month_name} ${year} ${time}"
}

# --------------------------------------------------------------------------------
# write_step_summary: use GitHub's official job summary API
# --------------------------------------------------------------------------------

write_step_summary()
{
    local file="${GITHUB_STEP_SUMMARY:-}"

    # If not running in GitHub Actions, nothing to do
    [[ -z "${file}" ]] && return 0

    {
        echo "## Job Status Overview"
        echo

        print_sorted_section "Successful jobs" "${success_list[@]}"
        print_sorted_section "Failed jobs" "${failed_list[@]}"
        print_sorted_section "Timed out jobs" "${timed_out_list[@]}"
        print_sorted_section "Cancelled jobs" "${cancelled_list[@]}"
        print_sorted_section "Skipped jobs" "${skipped_list[@]}"
        print_sorted_section "Other statuses" "${other_list[@]}"

        echo
        echo "### Workflow metadata"
        echo
        echo "| Field  | Value   |"
        echo "| :----- | :------ |"

        echo "| Repository | ${GITHUB_REPOSITORY} |"
        echo "| Workflow | ${GITHUB_WORKFLOW} |"
        echo "| Run number | #${GITHUB_RUN_NUMBER} |"
        echo "| Attempt | ${GITHUB_RUN_ATTEMPT} |"
        echo "| Event | ${GITHUB_EVENT_NAME} |"

        actor="${GITHUB_ACTOR:-unknown}"
        trigger="${GITHUB_TRIGGERING_ACTOR:-}"

        echo "| Actor | ${actor} |"
        if [[ -n "${trigger}" && "${trigger}" != "${actor}" ]]; then
            echo "| Triggering actor | ${trigger} |"
        fi

        echo "| Ref | ${GITHUB_REF_NAME} |"
        echo "| Commit SHA | ${GITHUB_SHA} |"
        echo "| Run URL | https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID} |"

        # Pull Request metadata (if applicable)
        if [[ -f "${GITHUB_EVENT_PATH}" ]]; then
            pr_number=$(jq -r '.pull_request.number // empty' "${GITHUB_EVENT_PATH}")
            pr_title=$(jq -r '.pull_request.title // empty' "${GITHUB_EVENT_PATH}")

            if [[ -n "${pr_number}" ]]; then
                echo "| PR | #${pr_number}: ${pr_title} |"
                echo "| PR URL | https://github.com/${GITHUB_REPOSITORY}/pull/${pr_number} |"
            fi
        fi

        generated_at="$(build_human_timestamp)"
        echo "| Generated at (UTC) | ${generated_at} |"
        echo

    } >> "${file}"
}

# --------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------

main()
{
    ensure_jq

    local job_results_json="${1:-}"

    # If no JSON was passed in, fetch from GitHub API (matrix-aware)
    if [[ -z "${job_results_json}" ]]; then
        job_results_json="$(fetch_jobs_json)" || {
            echo "ERROR: No job results JSON provided and failed to fetch from GitHub API."
            exit 1
        }
    fi

    parse_jobs "${job_results_json}"
    write_step_summary
}

main "$@"
