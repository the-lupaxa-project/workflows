#!/usr/bin/env python3
"""
GitHub Actions Slack workflow status notifier.

This script is designed to be run inside a GitHub Actions job. It:

  - Fetches job metadata for the current workflow run via the GitHub REST API
    (same endpoint and behaviour as check-jobs.py).
  - Buckets jobs into success/failure/cancelled/skipped/timed_out/other.
  - Computes an overall status for the workflow.
  - Sends a formatted Slack message via an incoming webhook.

Configuration is done via environment variables:

  SLACK_WEBHOOK_URL or CHECK_JOBS_SLACK_WEBHOOK
      - Slack incoming webhook URL.
      - If neither is set or they are empty, the script prints an info message
        and exits with code 0 without sending anything.

  SEND_TO_SLACK_RESULTS
      - Comma-separated list of overall statuses that should trigger a Slack
        notification. Valid values:
            success, failure, mixed, unknown
        Special value:
            all    -> notify on every result.
      - Default: "failure,mixed".

  SEND_TO_SLACK_INCLUDE_JOBS
      - Controls whether job details are included in the Slack message.
        Allowed values (case-insensitive):
            "true"       -> always include job details
            "false"      -> never include job details
            "on-failure" -> only include job details if overall status != success
      - Default: "on-failure".

  SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE
      - If set to "true" (case-insensitive), attempt to include the commit
        message or PR title in the Slack message, using GITHUB_EVENT_PATH.
      - Default: "true".

Environment variables required for GitHub API access:

  GITHUB_REPOSITORY  (e.g. "owner/repo")
  GITHUB_RUN_ID      (numeric ID of the current workflow run)
  GITHUB_TOKEN or ACTIONS_RUNTIME_TOKEN

This script is intentionally dependency-free (only uses the Python standard
library) so it can run on GitHub-hosted runners without additional setup.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Literal, NoReturn, Optional, Tuple
from urllib.error import HTTPError, URLError


JobRecord = Tuple[str, str]  # (raw_name, raw_result)
OverallStatus = Literal["success", "failure", "mixed", "unknown"]


# ---------------------------------------------------------------------------#
# Utility helpers
# ---------------------------------------------------------------------------#


def error(message: str, *, code: int = 1) -> NoReturn:
    """
    Print an error message to stderr and exit with the given status code.
    """
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def ordinal_suffix(day: int) -> str:
    """
    Return the HTML-like ordinal suffix for a given day of the month.
    """
    if day in (1, 21, 31):
        suf = "st"
    elif day in (2, 22):
        suf = "nd"
    elif day in (3, 23):
        suf = "rd"
    else:
        suf = "th"
    return suf


def build_human_timestamp() -> str:
    """
    Build a human-readable UTC timestamp similar to the original Bash script.

    Example:
        "Monday 24th November 2025 18:03:45"
    """
    now = datetime.now(timezone.utc)
    day = now.day
    suffix = ordinal_suffix(day)
    dow = now.strftime("%A")
    month_name = now.strftime("%B")
    year = now.strftime("%Y")
    time_str = now.strftime("%H:%M:%S")
    return f"{dow} {day}{suffix} {month_name} {year} {time_str}"


def strtobool(value: str, default: bool = False) -> bool:
    """
    Convert a string to a boolean using a small truthy/falsey set.
    """
    if value is None:
        return default
    value_lower = value.strip().lower()
    if value_lower in ("1", "true", "yes", "on"):
        return True
    if value_lower in ("0", "false", "no", "off"):
        return False
    return default


# ---------------------------------------------------------------------------#
# Input loading (API)
# ---------------------------------------------------------------------------#


def fetch_jobs_json_from_api() -> Dict[str, Any]:
    """
    Fetch job metadata for the current workflow run via the GitHub REST API.

    Environment variables used:
        - GITHUB_REPOSITORY        (required)
        - GITHUB_RUN_ID            (required)
        - GITHUB_TOKEN             (preferred)
        - ACTIONS_RUNTIME_TOKEN    (fallback if GITHUB_TOKEN is unset)
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACTIONS_RUNTIME_TOKEN")

    if not repo or not run_id:
        error("GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API.", code=1)

    if not token:
        error("GITHUB_TOKEN (or ACTIONS_RUNTIME_TOKEN) is not set; cannot call GitHub API.", code=1)

    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-send-to-slack",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body_bytes = resp.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if body:
            print(body, file=sys.stderr)
        error(f"GitHub API returned HTTP {exc.code} when fetching jobs: {exc.reason}", code=1)
    except URLError as exc:
        error(f"Failed to reach GitHub API: {exc.reason}", code=1)
    except Exception as exc:  # pragma: no cover - defensive catch-all
        error(f"Unexpected error when calling GitHub API: {exc}", code=1)

    if status != 200:
        body = body_bytes.decode("utf-8", errors="replace")
        print("GitHub API response body:", file=sys.stderr)
        print(body, file=sys.stderr)
        error(f"GitHub API returned HTTP {status} when fetching jobs.", code=1)

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode GitHub API JSON: {exc}", code=1)

    if not isinstance(data, dict):
        error("GitHub API returned JSON, but the top-level structure is not an object as expected.", code=1)

    return data


# ---------------------------------------------------------------------------#
# Normalisation and bucketing
# ---------------------------------------------------------------------------#


def normalise_job_name(raw: str) -> str:
    """
    Normalise a raw job name into a canonical form.

    - If the name contains a slash, keep only the right-hand side.
    - Strip leading/trailing whitespace.
    """
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    return raw.strip()


def should_skip_status_job(name: str) -> bool:
    """
    Determine whether a job name should be skipped as an umbrella/status job.

    Skips jobs such as:
      - "CI Status", "Status", "SomethingStatus"
      - "Slack ... Notification" (to avoid recursion for Slack jobs)

    This behaviour can be overridden by setting:
        CHECK_JOBS_INCLUDE_STATUS=1
    """
    if os.environ.get("CHECK_JOBS_INCLUDE_STATUS", "0") == "1":
        return False

    name_stripped = name.strip()
    if name_stripped.endswith(" Status") or name_stripped == "Status" or name_stripped.endswith("Status"):
        return True
    if name_stripped.startswith("Slack"):
        return True
    return False


def _extract_api_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    """
    Extract (name, conclusion) pairs from the GitHub /jobs API shape.

    Expected shape:
        {
          "jobs": [
            { "name": "...", "conclusion": "success", ... },
            ...
          ]
        }
    """
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return None

    records: List[JobRecord] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        raw_name = str(job.get("name", ""))
        conclusion = str(job.get("conclusion", "unknown") or "unknown")
        records.append((raw_name, conclusion))
    return records


def _extract_needs_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    """
    Extract (name, result) pairs from a toJson(needs)-style mapping.

    Expected shape:
        {
          "job_id": { "result": "success", ... },
          ...
        }

    Also looks for "conclusion" if "result" is not present.
    """
    if not isinstance(data, dict):
        return None

    records: List[JobRecord] = []
    for key, value in data.items():
        raw_name = str(key)
        if isinstance(value, dict):
            result = value.get("result") or value.get("conclusion") or "unknown"
        else:
            result = "unknown"
        records.append((raw_name, str(result)))
    return records


def bucket_jobs(data: Dict[str, Any]) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
    """
    Bucket jobs into status lists from a JSON object.

    Supports:
      - GitHub /jobs API format
      - toJson(needs) mapping
    """
    success: List[str] = []
    failure: List[str] = []
    cancelled: List[str] = []
    skipped: List[str] = []
    timed_out: List[str] = []
    other: List[str] = []

    job_records: Optional[Iterable[JobRecord]] = None

    if isinstance(data, dict):
        job_records = _extract_api_jobs(data)
        if job_records is None:
            job_records = _extract_needs_jobs(data)

    if not job_records:
        error("Unsupported JSON structure for job results.", code=1)

    assert job_records is not None

    buckets: Dict[str, List[str]] = {
        "success": success,
        "failure": failure,
        "cancelled": cancelled,
        "skipped": skipped,
        "timed_out": timed_out,
    }

    for raw_name, raw_result in job_records:
        job_name = normalise_job_name(raw_name)
        if not job_name or should_skip_status_job(job_name):
            continue

        result = raw_result or "unknown"
        bucket = buckets.get(result)
        if bucket is not None:
            bucket.append(job_name)
        else:
            other.append(f"{job_name}:{result}")

    return success, failure, cancelled, skipped, timed_out, other


def compute_overall_status(
    success: List[str],
    failure: List[str],
    cancelled: List[str],
    skipped: List[str],
    timed_out: List[str],
    other: List[str],
) -> OverallStatus:
    """
    Compute an overall status for the workflow.

    Heuristic:
      - If any failure or timed out jobs: "failure"
      - Else if any non-success (cancelled/skipped/other) and at least one success: "mixed"
      - Else if at least one success and nothing else: "success"
      - Else: "unknown"
    """
    if failure or timed_out:
        return "failure"

    has_success = bool(success)
    has_non_success = bool(cancelled or skipped or other)

    if has_success and has_non_success:
        return "mixed"

    if has_success and not has_non_success:
        return "success"

    return "unknown"


# ---------------------------------------------------------------------------#
# Metadata helpers
# ---------------------------------------------------------------------------#


def maybe_read_pr_metadata() -> Tuple[str, str]:
    """
    Attempt to read pull request metadata from GITHUB_EVENT_PATH.

    Returns (pr_number, pr_title) or ("", "") if not available.
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.isfile(event_path):
        return "", ""

    try:
        with open(event_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return "", ""

    pr = payload.get("pull_request") or {}
    number = pr.get("number")
    title = pr.get("title")

    if number:
        return str(number), str(title or "")
    return "", ""


def maybe_read_commit_message() -> str:
    """
    Attempt to read a human-friendly commit message or PR title from
    GITHUB_EVENT_PATH. This is best-effort and may return an empty string.
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.isfile(event_path):
        return ""

    try:
        with open(event_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return ""

    # Common cases:
    # - push event: payload["head_commit"]["message"]
    # - pull_request: payload["pull_request"]["title"]
    if "pull_request" in payload:
        pr = payload["pull_request"] or {}
        title = pr.get("title")
        if title:
            return str(title)

    head_commit = payload.get("head_commit") or {}
    message = head_commit.get("message")
    if message:
        return str(message)

    return ""


# ---------------------------------------------------------------------------#
# Slack formatting & sending
# ---------------------------------------------------------------------------#


def build_jobs_markdown(
    success: List[str],
    failure: List[str],
    cancelled: List[str],
    skipped: List[str],
    timed_out: List[str],
    other: List[str],
) -> str:
    """
    Build a Slack-friendly markdown summary of jobs grouped by status.
    """
    lines: List[str] = []

    def add_section(title: str, items: List[str]) -> None:
        if not items:
            return
        lines.append(f"*{title}*")
        for name in sorted(set(items), key=str.casefold):
            lines.append(f"• {name}")
        lines.append("")

    add_section("Successful jobs", success)
    add_section("Failed jobs", failure)
    add_section("Timed out jobs", timed_out)
    add_section("Cancelled jobs", cancelled)
    add_section("Skipped jobs", skipped)
    add_section("Other statuses", other)

    if not lines:
        lines.append("No jobs found in this run.")

    return "\n".join(lines).strip()


def build_slack_payload(
    overall_status: OverallStatus,
    job_markdown: Optional[str],
    include_commit_message: bool,
) -> Dict[str, Any]:
    """
    Build the Slack payload in a style similar to Gamesight/slack-workflow-status.
    """
    icon = {
        "success": ":white_check_mark:",
        "failure": ":x:",
        "mixed": ":warning:",
    }.get(overall_status, ":grey_question:")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    workflow = os.environ.get("GITHUB_WORKFLOW", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    ref_name = os.environ.get("GITHUB_REF_NAME", "")
    sha = os.environ.get("GITHUB_SHA", "")
    actor = os.environ.get("GITHUB_ACTOR", "unknown")

    pr_number, pr_title = maybe_read_pr_metadata()
    generated_at = build_human_timestamp()

    title_parts: List[str] = ["GitHub Actions workflow"]
    if workflow:
        title_parts.append(f"“{workflow}”")
    if repo:
        title_parts.append(f"for `{repo}`")
    title = " ".join(title_parts).strip()

    # Base text line
    text = f"{icon} {title} ({overall_status})"

    blocks: List[Dict[str, Any]] = []

    # Header block
    header_text_lines: List[str] = [f"*{title}*"]
    header_text_lines.append(f"*Status:* `{overall_status}`")
    header_text_lines.append(f"*Event:* `{event_name}`")
    if ref_name:
        header_text_lines.append(f"*Ref:* `{ref_name}`")
    if sha:
        header_text_lines.append(f"*SHA:* `{sha[:7]}`")
    header_text_lines.append(f"*Actor:* `{actor}`")

    if repo and run_id:
        run_url = f"https://github.com/{repo}/actions/runs/{run_id}"
        header_text_lines.append(f"*Run:* <{run_url}|View in GitHub>")

    if pr_number:
        if repo:
            pr_url = f"https://github.com/{repo}/pull/{pr_number}"
            header_text_lines.append(f"*PR:* <{pr_url}|#{pr_number}: {pr_title}>")
        else:
            header_text_lines.append(f"*PR:* #{pr_number}: {pr_title}")

    header_text_lines.append(f"*Generated at (UTC):* `{generated_at}`")

    header_block = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n".join(header_text_lines)},
    }
    blocks.append(header_block)

    # Optional commit message
    if include_commit_message:
        commit_message = maybe_read_commit_message()
        if commit_message:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Commit message / PR title:*\n>{commit_message}",
                    },
                }
            )

    # Optional job details
    if job_markdown:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": job_markdown},
            }
        )

    return {
        "text": text,
        "blocks": blocks,
    }


def send_slack(webhook_url: str, payload: Dict[str, Any]) -> None:
    """
    Send the given payload to Slack via the provided webhook URL.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            _ = resp.read()
    except Exception as exc:
        # Do not fail the whole job because Slack is unavailable
        print(f"WARNING: Failed to send Slack notification: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------#
# Entry point
# ---------------------------------------------------------------------------#


def main() -> None:
    """
    Entry point: fetch jobs, compute status, and send Slack notification
    according to environment configuration.
    """
    # Resolve webhook URL (first non-empty wins)
    webhook_url = (
        os.environ.get("SLACK_WEBHOOK_URL", "").strip()
        or os.environ.get("CHECK_JOBS_SLACK_WEBHOOK", "").strip()
    )
    if not webhook_url:
        print("No SLACK_WEBHOOK_URL or CHECK_JOBS_SLACK_WEBHOOK set; skipping Slack notification.")
        return

    # Fetch and bucket jobs
    data = fetch_jobs_json_from_api()
    success, failure, cancelled, skipped, timed_out, other = bucket_jobs(data)
    overall_status = compute_overall_status(success, failure, cancelled, skipped, timed_out, other)

    # Determine whether this status should trigger a notification
    results_raw = os.environ.get("SEND_TO_SLACK_RESULTS", "failure,mixed")
    results_raw = results_raw.strip().lower()
    if results_raw != "all":
        # Simple containment check on a comma-separated list
        wanted = [part.strip() for part in results_raw.split(",") if part.strip()]
        if wanted and overall_status not in wanted:
            print(f"Overall status '{overall_status}' not in SEND_TO_SLACK_RESULTS={results_raw!r}; skipping Slack notification.")
            return

    include_jobs_mode = os.environ.get("SEND_TO_SLACK_INCLUDE_JOBS", "on-failure").strip().lower()
    include_commit_message = strtobool(os.environ.get("SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE", "true"), default=True)

    # Decide whether to include job details
    job_markdown: Optional[str]
    if include_jobs_mode == "false":
        job_markdown = None
    elif include_jobs_mode == "true":
        job_markdown = build_jobs_markdown(success, failure, cancelled, skipped, timed_out, other)
    else:
        # on-failure (or unknown value -> treat as on-failure)
        if overall_status == "success":
            job_markdown = None
        else:
            job_markdown = build_jobs_markdown(success, failure, cancelled, skipped, timed_out, other)

    payload = build_slack_payload(overall_status, job_markdown, include_commit_message)
    send_slack(webhook_url, payload)


if __name__ == "__main__":
    main()
