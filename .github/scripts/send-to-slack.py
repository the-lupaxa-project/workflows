#!/usr/bin/env python3
"""
Slack workflow status notifier for GitHub Actions.

This script is a Python reimplementation of the core behaviour of
Gamesight/slack-workflow-status, adapted to run as a standalone script
inside a GitHub Actions job.

It:

  - Fetches the current workflow run and its jobs from the GitHub API
  - Filters jobs to those with status == "completed"
  - Determines a workflow color and message:
        "good" / "warning" / "danger"
        "Success:" / "Cancelled:" / "Failed:"
  - Builds per-job fields like:
        "✓ <job_link|job_name> (1m 23s)"
  - Builds a Slack attachment with:
        - status line (actor, event, branch / PR)
        - details line (workflow name, run number, duration)
        - optional commit message
        - footer with repo link
        - fields with job info (unless disabled)

Configuration (env vars):

  Required:
    SLACK_WEBHOOK_URL       Slack Incoming Webhook URL
    GITHUB_REPOSITORY       e.g. "owner/repo"
    GITHUB_RUN_ID           numeric ID of the current workflow run
    GITHUB_TOKEN or ACTIONS_RUNTIME_TOKEN

  Optional (behaviour):

    SEND_TO_SLACK_RESULTS
      Comma-separated list of workflow conclusions to notify on,
      e.g. "failure,cancelled,timed_out". Use "all" (default) to notify
      on every result.

    SEND_TO_SLACK_INCLUDE_JOBS
      "true"       -> always include job fields
      "false"      -> never include job fields
      "on-failure" -> include job fields only when workflow is not success
      Default: "true"

    SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE
      "true" (default) to append "Commit: <message>" to the text, using
      workflow_run.head_commit.message.

    SEND_TO_SLACK_JOBS_TO_FETCH
      Number of jobs to fetch per_page from the GitHub API. Default: "30".

  Optional (cosmetics, similar to Gamesight action inputs):

    SEND_TO_SLACK_CHANNEL      -> Slack channel (e.g. "#ci-status")
    SEND_TO_SLACK_NAME         -> Bot display name
    SEND_TO_SLACK_ICON_URL     -> Icon image URL
    SEND_TO_SLACK_ICON_EMOJI   -> Icon emoji (e.g. ":wolf:")

This script intentionally uses only the Python standard library.
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
    """
    Parse an ISO 8601 timestamp from the GitHub API into a naive UTC datetime.

    GitHub typically returns timestamps like "2025-11-24T18:03:45Z".
    """
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    # Replace trailing Z with +00:00 so fromisoformat can handle it
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    # Convert to naive UTC for easier duration math
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


def compute_duration(start: datetime, end: datetime) -> str:
    """
    Compute a duration string like "1d 2h 3m 4s" between two datetimes.

    This mirrors the TypeScript compute_duration implementation from the
    original Gamesight action.
    """
    duration_ms = (end - start).total_seconds()
    if duration_ms < 0:
        duration_ms = 0
    delta = int(duration_ms)

    days = delta // 86400
    delta -= days * 86400
    hours = (delta // 3600) % 24
    delta -= hours * 3600
    minutes = (delta // 60) % 60
    delta -= minutes * 60
    seconds = delta % 60

    def format_duration(value: int, text: str, hide_on_zero: bool) -> str:
        if value <= 0 and hide_on_zero:
            return ""
        return f"{value}{text} "

    result = (
        format_duration(days, "d", True)
        + format_duration(hours, "h", True)
        + format_duration(minutes, "m", True)
        + format_duration(seconds, "s", False)
    ).strip()

    if not result:
        return "0s"
    return result


def fetch_json(url: str, token: str, user_agent: str) -> Dict[str, Any]:
    """
    Fetch a JSON object from the GitHub API with basic error handling.
    """
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


# --------------------------------------------------------------------------- #
# GitHub data loading (run + jobs)
# --------------------------------------------------------------------------- #


def fetch_run_and_jobs(
    repo: str, run_id: str, token: str, jobs_to_fetch: int
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Fetch workflow run metadata and jobs from the GitHub API.

    Returns:
        (workflow_run, completed_jobs)
    """
    base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"

    run = fetch_json(base, token, "lupaxa-send-to-slack")
    jobs_data = fetch_json(f"{base}/jobs?per_page={jobs_to_fetch}", token, "lupaxa-send-to-slack")

    jobs_raw = jobs_data.get("jobs", [])
    if not isinstance(jobs_raw, list):
        jobs_raw = []

    completed_jobs = [
        job for job in jobs_raw if isinstance(job, dict) and job.get("status") == "completed"
    ]

    return run, completed_jobs


def get_workflow_conclusion(workflow_run: Dict[str, Any]) -> str:
    """
    Determine the overall conclusion for the workflow run.

    Use workflow_run.conclusion if present, otherwise fall back to workflow_run.status.
    """
    conclusion = (workflow_run.get("conclusion") or "").strip().lower()
    status = (workflow_run.get("status") or "").strip().lower()

    if conclusion:
        return conclusion
    if status:
        return status
    return "unknown"


# --------------------------------------------------------------------------- #
# Slack payload construction (mirroring Gamesight)
# --------------------------------------------------------------------------- #


def determine_workflow_color_and_msg(completed_jobs: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Determine workflow_color and workflow_msg based on job conclusions.

    Mirrors:

      if all jobs are success/skipped:
          color = "good", msg = "Success:"
      elif any job cancelled:
          color = "warning", msg = "Cancelled:"
      else:
          color = "danger", msg = "Failed:"
    """
    if not completed_jobs:
        # No completed jobs, treat as warning
        return "warning", "Unknown:"

    conclusions = [str(job.get("conclusion") or "").lower() for job in completed_jobs]

    if all(c in ("success", "skipped") for c in conclusions):
        return "good", "Success:"

    if any(c == "cancelled" for c in conclusions):
        return "warning", "Cancelled:"

    # Otherwise, treat as failure
    return "danger", "Failed:"


def build_job_fields(
    completed_jobs: List[Dict[str, Any]],
    include_jobs_mode: str,
    workflow_color_msg: Tuple[str, str],
    workflow_conclusion: str,
) -> List[Dict[str, Any]]:
    """
    Build the Slack fields array for jobs, respecting include_jobs_mode.

    Job field format:
      {
        "title": "",
        "short": true,
        "value": "✓ <job_html_url|job.name> (1m 23s)"
      }
    """
    include_jobs_mode = (include_jobs_mode or "true").strip().lower()
    workflow_color, workflow_msg = workflow_color_msg  # noqa: F841 (may be unused)

    if include_jobs_mode == "false":
        return []

    # For "on-failure", if the overall conclusion is success/skipped-only, skip jobs
    if include_jobs_mode == "on-failure":
        # We mimic Gamesight's logic (they only look at job conclusions),
        # but here we use workflow_conclusion as a proxy.
        if workflow_conclusion == "success":
            return []

    fields: List[Dict[str, Any]] = []

    for job in completed_jobs:
        conclusion = str(job.get("conclusion") or "").lower()
        name = str(job.get("name") or "").strip()
        html_url = str(job.get("html_url") or "").strip()

        if not name or not html_url:
            continue

        if conclusion == "success":
            job_status_icon = "✓"
        elif conclusion in ("cancelled", "skipped"):
            job_status_icon = "⃠"
        else:
            job_status_icon = "✗"

        started_at = parse_iso8601(job.get("started_at"))
        completed_at = parse_iso8601(job.get("completed_at"))
        if started_at and completed_at:
            job_duration = compute_duration(started_at, completed_at)
            value = f"{job_status_icon} <{html_url}|{name}> ({job_duration})"
        else:
            value = f"{job_status_icon} <{html_url}|{name}>"

        fields.append(
            {
                "title": "",  # Matches the TS hack: empty title, short field
                "short": True,
                "value": value,
            }
        )

    return fields


def build_pull_request_string(workflow_run: Dict[str, Any]) -> str:
    """
    Build the pull request description string, excluding PRs from external repos.

    Format mirrors TS:
      "<repo_url/pull/num|#num> from `head.ref` to `base.ref`"
    """
    repository = workflow_run.get("repository") or {}
    repo_url = str(repository.get("url") or "")
    html_url = str(repository.get("html_url") or "")

    pull_requests = workflow_run.get("pull_requests") or []
    if not isinstance(pull_requests, list):
        pull_requests = []

    parts: List[str] = []

    for pr in pull_requests:
        if not isinstance(pr, dict):
            continue

        base = pr.get("base") or {}
        head = pr.get("head") or {}

        base_repo = base.get("repo") or {}
        base_repo_url = str(base_repo.get("url") or "")

        # Exclude PRs from external repositories
        if base_repo_url != repo_url:
            continue

        number = pr.get("number")
        head_ref = str((head.get("ref") or "")).strip()
        base_ref = str((base.get("ref") or "")).strip()

        if number is None:
            continue

        link = f"{html_url}/pull/{number}" if html_url else ""
        if link:
            parts.append(
                f"<{link}|#{number}> from `{head_ref}` to `{base_ref}`"
            )

    return ", ".join(parts)


def build_slack_payload(
    workflow_run: Dict[str, Any],
    completed_jobs: List[Dict[str, Any]],
    include_jobs_mode: str,
    include_commit_message: bool,
) -> Dict[str, Any]:
    """
    Build the Slack webhook payload, mirroring Gamesight's formatting.
    """
    workflow_color, workflow_msg = determine_workflow_color_and_msg(completed_jobs)
    workflow_conclusion = get_workflow_conclusion(workflow_run)

    # Duration of the whole workflow
    created_at = parse_iso8601(workflow_run.get("created_at"))
    updated_at = parse_iso8601(workflow_run.get("updated_at"))
    workflow_duration = ""
    if created_at and updated_at:
        workflow_duration = compute_duration(created_at, updated_at)

    repository = workflow_run.get("repository") or {}
    repo_full_name = str(repository.get("full_name") or "").strip()
    repo_html_url = str(repository.get("html_url") or "").strip()

    head_branch = str(workflow_run.get("head_branch") or "").strip()
    head_commit = workflow_run.get("head_commit") or {}
    head_commit_message = str(head_commit.get("message") or "").strip()

    workflow_run_html_url = str(workflow_run.get("html_url") or "").strip()
    run_number = workflow_run.get("run_number")

    # repo_url and branch_url (Slack links)
    repo_url = f"<{repo_html_url}|*{repo_full_name}*>" if repo_html_url and repo_full_name else ""
    branch_url = (
        f"<{repo_html_url}/tree/{head_branch}|*{head_branch}*>"
        if repo_html_url and head_branch
        else head_branch
    )
    workflow_run_url = (
        f"<{workflow_run_html_url}|#{run_number}>" if workflow_run_html_url and run_number else ""
    )

    # Context env variables
    actor = os.environ.get("GITHUB_ACTOR", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    workflow_name = os.environ.get("GITHUB_WORKFLOW", "")

    # Build status_string
    # Default:
    #   `${workflow_msg} ${context.actor}'s \`${context.eventName}\` on \`${branch_url}\``
    status_string = (
        f"{workflow_msg} {actor}'s `{event_name}` on `{branch_url}`"
        if branch_url
        else f"{workflow_msg} {actor}'s `{event_name}`"
    )

    # Build PR string, override status_string if PR present
    pull_requests_string = build_pull_request_string(workflow_run)
    if pull_requests_string:
        status_string = (
            f"{workflow_msg} {actor}'s `pull_request` {pull_requests_string}"
        )

    # details_string:
    #   `Workflow: ${context.workflow} ${workflow_run_url} completed in \`${workflow_duration}\``
    details_parts: List[str] = []
    details_parts.append("Workflow:")
    if workflow_name:
        details_parts.append(workflow_name)
    if workflow_run_url:
        details_parts.append(workflow_run_url)
    details_text = " ".join(details_parts).strip()

    if workflow_duration:
        details_text = f"{details_text} completed in `{workflow_duration}`"
    else:
        details_text = f"{details_text} completed"

    # Commit message string
    commit_message_text = f"Commit: {head_commit_message}" if head_commit_message else ""

    # Job fields
    job_fields = build_job_fields(
        completed_jobs=completed_jobs,
        include_jobs_mode=include_jobs_mode,
        workflow_color_msg=(workflow_color, workflow_msg),
        workflow_conclusion=workflow_conclusion,
    )

    # Build Slack attachment
    text_lines: List[str] = [status_string, details_text]
    if include_commit_message and commit_message_text:
        text_lines.append(commit_message_text)

    attachment: Dict[str, Any] = {
        "mrkdwn_in": ["text"],
        "color": workflow_color,
        "text": "\n".join(text_lines),
        "footer": repo_url,
        "footer_icon": "https://github.githubassets.com/favicon.ico",
        "fields": job_fields,
    }

    # Base payload
    payload: Dict[str, Any] = {
        "attachments": [attachment],
    }

    # Optional cosmetics
    channel = os.environ.get("SEND_TO_SLACK_CHANNEL") or os.environ.get("SLACK_CHANNEL")
    if channel:
        payload["channel"] = channel

    username = os.environ.get("SEND_TO_SLACK_NAME") or os.environ.get("SLACK_NAME")
    if username:
        payload["username"] = username

    icon_emoji = os.environ.get("SEND_TO_SLACK_ICON_EMOJI") or os.environ.get("SLACK_ICON_EMOJI")
    if icon_emoji:
        payload["icon_emoji"] = icon_emoji

    icon_url = os.environ.get("SEND_TO_SLACK_ICON_URL") or os.environ.get("SLACK_ICON_URL")
    if icon_url:
        payload["icon_url"] = icon_url

    return payload


def post_to_slack(webhook_url: str, payload: Dict[str, Any]) -> None:
    """
    Send the payload to the Slack Incoming Webhook URL.
    """
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(webhook_url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            _ = resp.read()
    except HTTPError as exc:
        resp_body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if resp_body:
            print(resp_body, file=sys.stderr)
        error(f"Slack webhook returned HTTP {exc.code}: {exc.reason}", code=1)
    except URLError as exc:
        error(f"Failed to reach Slack webhook: {exc.reason}", code=1)
    except Exception as exc:  # pragma: no cover - defensive
        error(f"Unexpected error when calling Slack webhook: {exc}", code=1)

    if not (200 <= status < 300):
        error(f"Slack webhook returned HTTP {status}", code=1)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    """
    Entry point:

      - Load env configuration
      - Fetch workflow run + jobs
      - Optionally skip based on SEND_TO_SLACK_RESULTS
      - Build Slack payload mirroring Gamesight format
      - POST to Slack
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

    jobs_to_fetch_raw = os.environ.get("SEND_TO_SLACK_JOBS_TO_FETCH", "30")
    try:
        jobs_to_fetch = int(jobs_to_fetch_raw)
    except ValueError:
        jobs_to_fetch = 30

    workflow_run, completed_jobs = fetch_run_and_jobs(repo, run_id, token, jobs_to_fetch)
    workflow_conclusion = get_workflow_conclusion(workflow_run)

    # Decide whether to notify at all (extension: not in original TS, but useful)
    results_setting = os.environ.get("SEND_TO_SLACK_RESULTS", "all").strip().lower()
    if results_setting != "all":
        allowed = {s.strip() for s in results_setting.split(",") if s.strip()}
        if allowed and workflow_conclusion not in allowed:
            print(
                f"Workflow conclusion '{workflow_conclusion}' not in "
                f"SEND_TO_SLACK_RESULTS={results_setting!r}; skipping Slack notification.",
                file=sys.stderr,
            )
            return

    include_jobs_mode = os.environ.get("SEND_TO_SLACK_INCLUDE_JOBS", "true")
    include_commit_message_raw = os.environ.get("SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE", "true")
    include_commit_message = include_commit_message_raw.strip().lower() == "true"

    payload = build_slack_payload(
        workflow_run=workflow_run,
        completed_jobs=completed_jobs,
        include_jobs_mode=include_jobs_mode,
        include_commit_message=include_commit_message,
    )
    post_to_slack(webhook_url, payload)


if __name__ == "__main__":
    main()
