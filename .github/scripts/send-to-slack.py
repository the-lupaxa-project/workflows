#!/usr/bin/env python3
"""
Slack workflow status notifier for GitHub Actions.

This script is designed to be run inside a GitHub Actions job at the *end* of a
workflow. It fetches the current workflow run and its jobs via the GitHub REST
API, builds a Slack message similar in spirit to Gamesight/slack-workflow-status,
and posts it to an Incoming Webhook URL.

Environment variables used:

  Required:
    - GITHUB_REPOSITORY        (e.g. "owner/repo")
    - GITHUB_RUN_ID            (numeric ID of the current workflow run)
    - GITHUB_TOKEN or ACTIONS_RUNTIME_TOKEN
    - SLACK_WEBHOOK_URL        (the Slack incoming webhook URL)

  Optional behaviour flags (typically set from a reusable workflow):

    - SEND_TO_SLACK_RESULTS
        Comma-separated list of results that should trigger a Slack notification:
          e.g. "failure,cancelled,timed_out"
        Use "all" (default) to notify on every result.

    - SEND_TO_SLACK_INCLUDE_JOBS
        Controls whether job details are included:
          "true"       -> include all jobs
          "false"      -> no job details
          "on-failure" -> only include jobs if the workflow failed
        Default: "true"

    - SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE
        "true" (default) to include the head commit message (first line).

  Optional cosmetic overrides:

    - SEND_TO_SLACK_CHANNEL       (Slack channel name, e.g. "#ci-status")
    - SEND_TO_SLACK_USERNAME      (bot display name)
    - SEND_TO_SLACK_ICON_EMOJI    (e.g. ":wolf:")
    - SEND_TO_SLACK_ICON_URL      (URL to an image to use as the icon)

The Slack payload uses classic Incoming Webhook attachments with:

  - A summary line:
      ":white_check_mark: Workflow *CI* in `owner/repo` on `branch` succeeded in `1m 23s`"

  - Fields:
      Actor, Event, Branch, Workflow, Status, Duration, Run URL, PR, Commit, etc.

  - Optional "Jobs" field with one line per job:
      ":white_check_mark: tests (45s)"
      ":x: lint (12s)"

This script is dependency-free (only Python standard library).
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, NoReturn, Optional, Tuple
from urllib.error import HTTPError, URLError


# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #


def error(message: str, *, code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit with the given status code."""
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp from the GitHub API into a timezone-aware datetime."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    # GitHub uses e.g. "2025-11-24T18:03:45Z"
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_duration(seconds: float) -> str:
    """Format a duration in seconds as '1h 2m 3s' (or smaller units as appropriate)."""
    total = int(round(seconds))
    if total < 0:
        total = 0
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)

    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts or sec:
        parts.append(f"{sec}s")
    return " ".join(parts)


def fetch_json(url: str, token: str, user_agent: str) -> Dict[str, Any]:
    """Fetch a JSON document from the GitHub API with basic error handling."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": user_agent,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, headers=headers)

    status: int = 0
    body_bytes: bytes = b""

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body_bytes = resp.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if body:
            print(body, file=sys.stderr)
        error(f"GitHub API returned HTTP {exc.code} for {url}: {exc.reason}", code=1)
    except URLError as exc:
        error(f"Failed to reach GitHub API: {exc.reason}", code=1)
    except Exception as exc:  # pragma: no cover - defensive
        error(f"Unexpected error when calling GitHub API: {exc}", code=1)

    if status != 200:
        body = body_bytes.decode("utf-8", errors="replace")
        print(f"GitHub API response body from {url}:", file=sys.stderr)
        print(body, file=sys.stderr)
        error(f"GitHub API returned HTTP {status} for {url}.", code=1)

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode JSON from {url}: {exc}", code=1)

    if not isinstance(data, dict):
        error(f"GitHub API returned JSON from {url}, but top-level is not an object.", code=1)

    return data


def maybe_read_pr_metadata() -> Tuple[str, str]:
    """
    Attempt to read pull request metadata from GITHUB_EVENT_PATH.

    Returns:
        (pr_number, pr_title) or ("", "") if not a PR event or parsing fails.
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


# --------------------------------------------------------------------------- #
# GitHub data loading
# --------------------------------------------------------------------------- #


def fetch_run_and_jobs(repo: str, run_id: str, token: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Fetch workflow run metadata and jobs from the GitHub API.

    Returns:
        (run, jobs_list)
    """
    base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"

    run = fetch_json(base, token, "lupaxa-send-to-slack")
    jobs_data = fetch_json(f"{base}/jobs?per_page=100", token, "lupaxa-send-to-slack")

    jobs_raw = jobs_data.get("jobs", [])
    if not isinstance(jobs_raw, list):
        jobs_raw = []

    return run, [j for j in jobs_raw if isinstance(j, dict)]


def get_overall_result(run: Dict[str, Any]) -> str:
    """
    Determine the overall result of the workflow run.

    Prefer the 'conclusion' field; fall back to 'status' if needed.
    """
    conclusion = (run.get("conclusion") or "").strip().lower()
    status = (run.get("status") or "").strip().lower()

    if conclusion:
        return conclusion
    if status:
        return status
    return "unknown"


# --------------------------------------------------------------------------- #
# Slack payload construction
# --------------------------------------------------------------------------- #


def status_emoji_and_color(result: str) -> Tuple[str, str]:
    """Map a workflow conclusion to a Slack emoji and attachment color."""
    result = (result or "").lower()

    emoji_map = {
        "success": ":white_check_mark:",
        "failure": ":x:",
        "cancelled": ":no_entry_sign:",
        "canceled": ":no_entry_sign:",
        "timed_out": ":alarm_clock:",
        "neutral": ":grey_question:",
        "skipped": ":fast_forward:",
        "action_required": ":warning:",
        "stale": ":warning:",
    }

    color_map = {
        "success": "#2eb886",      # green
        "failure": "#e01e5a",      # red
        "cancelled": "#8c8c8c",    # grey
        "canceled": "#8c8c8c",
        "timed_out": "#e3b341",    # yellow/orange
        "neutral": "#439fe0",      # blue
        "skipped": "#439fe0",
        "action_required": "#e3b341",
        "stale": "#8c8c8c",
    }

    emoji = emoji_map.get(result, ":grey_question:")
    color = color_map.get(result, "#439fe0")
    return emoji, color


def human_status_phrase(result: str) -> str:
    """Map a workflow conclusion to a human-readable phrase."""
    result = (result or "").lower()
    if result == "success":
        return "succeeded"
    if result == "failure":
        return "failed"
    if result in ("cancelled", "canceled"):
        return "was cancelled"
    if result == "timed_out":
        return "timed out"
    if result == "skipped":
        return "was skipped"
    if result == "action_required":
        return "requires action"
    if result == "neutral":
        return "completed (neutral)"
    if result == "stale":
        return "completed (stale)"
    if result == "completed":
        return "completed"
    if result == "in_progress":
        return "is in progress"
    if result == "queued":
        return "is queued"
    return f"completed with status '{result or 'unknown'}'"


def build_jobs_text(
    jobs: List[Dict[str, Any]],
    include_mode: str,
    overall_result: str,
) -> str:
    """
    Build a multi-line string describing each job's status and duration.

    Example line:
        ":white_check_mark: tests (45s)"
    """
    include_mode = (include_mode or "true").strip().lower()
    if include_mode == "false":
        return ""
    if include_mode == "on-failure" and overall_result == "success":
        return ""

    lines: List[str] = []

    for job in jobs:
        name = str(job.get("name", "")).strip()
        if not name:
            continue

        conclusion = str(job.get("conclusion") or job.get("status") or "unknown").lower()

        # Emoji for job-level status
        emoji, _ = status_emoji_and_color(conclusion)

        started = parse_iso8601(job.get("started_at"))
        completed = parse_iso8601(job.get("completed_at"))
        duration_str = ""

        if started and completed:
            duration_str = format_duration((completed - started).total_seconds())

        if duration_str:
            lines.append(f"{emoji} {name} ({duration_str})")
        else:
            lines.append(f"{emoji} {name}")

    return "\n".join(lines)


def build_slack_payload(
    run: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    overall_result: str,
    include_jobs_mode: str,
    include_commit_message: bool,
) -> Dict[str, Any]:
    """
    Build the JSON payload for the Slack Incoming Webhook.

    This aims to mirror the information content of Gamesight/slack-workflow-status:
    - Actor, Event, Branch, Workflow Name, Status, Run Duration
    - Optional job statuses and durations
    - Optional commit message
    """
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    actor_env = os.environ.get("GITHUB_ACTOR", "")
    event_env = os.environ.get("GITHUB_EVENT_NAME", "")
    branch_env = os.environ.get("GITHUB_REF_NAME", "")
    workflow_env = os.environ.get("GITHUB_WORKFLOW", "")

    # Run-level fields from the API
    head_branch = str(run.get("head_branch") or "").strip()
    head_sha = str(run.get("head_sha") or "").strip()
    event = str(run.get("event") or event_env or "").strip()
    workflow_name = str(run.get("name") or workflow_env or "").strip()
    actor = actor_env or (run.get("actor") or {}).get("login", "") or ""

    # Duration for the whole workflow
    started_at = parse_iso8601(run.get("run_started_at") or run.get("created_at"))
    updated_at = parse_iso8601(run.get("updated_at"))
    duration_str = ""
    if started_at and updated_at:
        duration_str = format_duration((updated_at - started_at).total_seconds())

    emoji, color = status_emoji_and_color(overall_result)
    status_phrase = human_status_phrase(overall_result)

    branch = branch_env or head_branch
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if repo and run_id else ""

    # Commit message (first line)
    commit_message_title = ""
    if include_commit_message:
        head_commit = run.get("head_commit") or {}
        raw_msg = str(head_commit.get("message") or "").strip()
        if raw_msg:
            first_line = raw_msg.splitlines()[0].strip()
            if len(first_line) > 200:
                first_line = first_line[:197] + "..."
            commit_message_title = first_line

    pr_number, pr_title = maybe_read_pr_metadata()

    # Summary line at the top of the Slack message
    summary_parts: List[str] = []

    if workflow_name:
        summary_parts.append(f"*{workflow_name}*")
    if repo:
        summary_parts.append(f"in `{repo}`")
    if branch:
        summary_parts.append(f"on `{branch}`")

    summary_text = " ".join(summary_parts) if summary_parts else "Workflow run"

    if duration_str:
        summary_text = f"{summary_text} {status_phrase} in `{duration_str}`"
    else:
        summary_text = f"{summary_text} {status_phrase}"

    summary_text = f"{emoji} {summary_text}"

    # Build fields
    fields: List[Dict[str, Any]] = []

    if actor:
        fields.append({"title": "Actor", "value": actor, "short": True})
    if event:
        fields.append({"title": "Event", "value": event, "short": True})
    if branch:
        fields.append({"title": "Branch", "value": branch, "short": True})
    if workflow_name:
        fields.append({"title": "Workflow", "value": workflow_name, "short": True})

    fields.append({"title": "Status", "value": overall_result or "unknown", "short": True})
    if duration_str:
        fields.append({"title": "Duration", "value": duration_str, "short": True})

    if run_url:
        fields.append({"title": "Run URL", "value": run_url, "short": False})

    if head_sha:
        fields.append({"title": "Commit SHA", "value": head_sha, "short": True})

    if pr_number:
        pr_link = f"https://github.com/{repo}/pull/{pr_number}" if repo else ""
        if pr_link:
            fields.append(
                {
                    "title": "Pull Request",
                    "value": f"<{pr_link}|#{pr_number}: {pr_title}>",
                    "short": False,
                }
            )

    if commit_message_title:
        fields.append(
            {
                "title": "Commit message",
                "value": commit_message_title,
                "short": False,
            }
        )

    # Jobs (optional)
    jobs_text = build_jobs_text(jobs, include_jobs_mode, overall_result)
    if jobs_text:
        fields.append(
            {
                "title": "Jobs",
                "value": jobs_text,
                "short": False,
            }
        )

    # Top-level payload
    payload: Dict[str, Any] = {
        "attachments": [
            {
                "color": color,
                "mrkdwn_in": ["text", "fields"],
                "text": summary_text,
                "fields": fields,
            }
        ]
    }

    # Optional cosmetics
    channel = os.environ.get("SEND_TO_SLACK_CHANNEL")
    if channel:
        payload["channel"] = channel

    username = os.environ.get("SEND_TO_SLACK_USERNAME")
    if username:
        payload["username"] = username

    icon_emoji = os.environ.get("SEND_TO_SLACK_ICON_EMOJI")
    if icon_emoji:
        payload["icon_emoji"] = icon_emoji

    icon_url = os.environ.get("SEND_TO_SLACK_ICON_URL")
    if icon_url:
        payload["icon_url"] = icon_url

    return payload


def post_to_slack(webhook_url: str, payload: Dict[str, Any]) -> None:
    """Send the payload to the Slack Incoming Webhook URL."""
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(webhook_url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            resp_body = resp.read().decode("utf-8", errors="replace").strip()
    except HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if body_err:
            print(body_err, file=sys.stderr)
        error(f"Slack webhook returned HTTP {exc.code}: {exc.reason}", code=1)
    except URLError as exc:
        error(f"Failed to reach Slack webhook: {exc.reason}", code=1)
    except Exception as exc:  # pragma: no cover - defensive
        error(f"Unexpected error when calling Slack webhook: {exc}", code=1)

    if not (200 <= status < 300):
        error(f"Slack webhook returned HTTP {status}: {resp_body}", code=1)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    """
    Entry point for the Slack notifier.

    Behaviour:
      - Fetch the workflow run and its jobs from the GitHub API.
      - Decide whether to notify based on SEND_TO_SLACK_RESULTS.
      - Build a Slack payload with summary + metadata + optional jobs & commit.
      - POST to SLACK_WEBHOOK_URL.
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("slack_webhook_url")
    if not webhook_url:
        error("SLACK_WEBHOOK_URL environment variable is required.", code=1)

    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACTIONS_RUNTIME_TOKEN")

    if not repo or not run_id:
        error("GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API.", code=1)
    if not token:
        error("GITHUB_TOKEN (or ACTIONS_RUNTIME_TOKEN) is not set; cannot call GitHub API.", code=1)

    run, jobs = fetch_run_and_jobs(repo, run_id, token)
    overall_result = get_overall_result(run)

    # Decide whether to notify at all, based on SEND_TO_SLACK_RESULTS
    results_setting = os.environ.get("SEND_TO_SLACK_RESULTS", "all").strip().lower()
    if results_setting != "all":
        allowed = {s.strip() for s in results_setting.split(",") if s.strip()}
        if allowed and overall_result not in allowed:
            print(
                f"Overall result '{overall_result}' not in SEND_TO_SLACK_RESULTS; "
                "skipping Slack notification.",
                file=sys.stderr,
            )
            return

    include_jobs_mode = os.environ.get("SEND_TO_SLACK_INCLUDE_JOBS", "true")
    include_commit_message = (
        os.environ.get("SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE", "true").strip().lower() == "true"
    )

    payload = build_slack_payload(
        run=run,
        jobs=jobs,
        overall_result=overall_result,
        include_jobs_mode=include_jobs_mode,
        include_commit_message=include_commit_message,
    )

    post_to_slack(webhook_url, payload)


if __name__ == "__main__":
    main()
