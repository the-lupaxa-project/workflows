#!/usr/bin/env python3
"""
Slack workflow status notifier for GitHub Actions.

Dependency-free Slack notifier for GitHub Actions workflow runs.

It fetches the current workflow run and its jobs from the GitHub REST API,
derives a workflow status from completed jobs, and posts a Slack Incoming
Webhook message.

Key behaviour:
  - Fetches all GitHub job pages.
  - Ignores selected jobs case-insensitively after normalising job names.
  - Ignores common notification/status jobs by default.
  - Uses only the first line of the commit message.
  - Can include per-job Slack fields.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple
from urllib.error import HTTPError, URLError


DEFAULT_JOBS_PER_PAGE = 100
DEFAULT_IGNORED_JOBS = {
    "check jobs status",
    "slack workflow status",
}


# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #


def error(message: str, *, code: int = 1) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)

    return dt


def compute_duration(start: datetime, end: datetime) -> str:
    duration_seconds = (end - start).total_seconds()
    if duration_seconds < 0:
        duration_seconds = 0

    delta = int(duration_seconds)

    days = delta // 86400
    delta -= days * 86400

    hours = delta // 3600
    delta -= hours * 3600

    minutes = delta // 60
    delta -= minutes * 60

    seconds = delta

    parts: List[str] = []

    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    return " ".join(parts)


def parse_next_link(link_header: str) -> Optional[str]:
    if not link_header:
        return None

    for part in link_header.split(","):
        section = part.strip()
        match = re.match(r'<([^>]+)>;\s*rel="([^"]+)"', section)
        if not match:
            continue

        url, rel = match.groups()
        if rel == "next":
            return url

    return None


def fetch_json_with_next(
    url: str,
    token: str,
    user_agent: str,
) -> Tuple[Dict[str, Any], Optional[str]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": user_agent,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body_bytes = resp.read()
            link_header = resp.headers.get("Link", "")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if body:
            print(body, file=sys.stderr)
        error(f"GitHub API returned HTTP {exc.code} for {url}: {exc.reason}")
    except URLError as exc:
        error(f"Failed to reach GitHub API at {url}: {exc.reason}")
    except Exception as exc:  # pragma: no cover - defensive
        error(f"Unexpected error when calling GitHub API at {url}: {exc}")

    if status != 200:
        body = body_bytes.decode("utf-8", errors="replace")
        if body:
            print(f"GitHub API response body from {url}:", file=sys.stderr)
            print(body, file=sys.stderr)
        error(f"GitHub API returned HTTP {status} for {url}.")

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode JSON from {url}: {exc}")

    if not isinstance(data, dict):
        error(f"GitHub API returned JSON from {url}, but top-level is not an object.")

    return data, parse_next_link(link_header)


def fetch_json(url: str, token: str, user_agent: str) -> Dict[str, Any]:
    data, _next_url = fetch_json_with_next(url, token, user_agent)
    return data


def normalise_job_name(raw: str) -> str:
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    return raw.strip()


def parse_ignored_jobs(raw: str) -> Set[str]:
    ignored: Set[str] = set()

    for part in raw.split(","):
        name = normalise_job_name(part)
        if name:
            ignored.add(name.casefold())

    return ignored


def build_ignored_jobs() -> Set[str]:
    ignored = set(DEFAULT_IGNORED_JOBS)

    raw_ignored_jobs = os.environ.get("SEND_TO_SLACK_IGNORE_JOBS", "")
    if raw_ignored_jobs.strip():
        ignored.update(parse_ignored_jobs(raw_ignored_jobs))

    return ignored


def first_line(value: str) -> str:
    return value.splitlines()[0].strip() if value.strip() else ""


# --------------------------------------------------------------------------- #
# GitHub data loading
# --------------------------------------------------------------------------- #


def fetch_run_and_jobs(
    repo: str,
    run_id: str,
    token: str,
    jobs_per_page: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if jobs_per_page <= 0:
        jobs_per_page = DEFAULT_JOBS_PER_PAGE

    if jobs_per_page > 100:
        jobs_per_page = 100

    base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"

    run = fetch_json(base, token, "lupaxa-send-to-slack")

    jobs_url: Optional[str] = f"{base}/jobs?per_page={jobs_per_page}"
    all_jobs: List[Dict[str, Any]] = []

    while jobs_url:
        jobs_data, next_url = fetch_json_with_next(
            jobs_url,
            token,
            "lupaxa-send-to-slack",
        )

        jobs_raw = jobs_data.get("jobs", [])
        if isinstance(jobs_raw, list):
            for job in jobs_raw:
                if isinstance(job, dict):
                    all_jobs.append(job)

        jobs_url = next_url

    completed_jobs = [
        job for job in all_jobs if str(job.get("status") or "").lower() == "completed"
    ]

    if not completed_jobs:
        print(
            "Warning: No completed jobs found for this workflow run. "
            "Slack notification will contain no job fields.",
            file=sys.stderr,
        )

    return run, completed_jobs


def get_workflow_conclusion(workflow_run: Dict[str, Any]) -> str:
    conclusion = str(workflow_run.get("conclusion") or "").strip().lower()
    status = str(workflow_run.get("status") or "").strip().lower()

    if conclusion:
        return conclusion
    if status:
        return status
    return "unknown"


def derive_workflow_conclusion_from_jobs(
    completed_jobs: List[Dict[str, Any]],
    ignored_job_names: Optional[Set[str]] = None,
) -> str:
    filtered_jobs: List[Dict[str, Any]] = []
    ignored = ignored_job_names or set()

    for job in completed_jobs:
        name = normalise_job_name(str(job.get("name") or ""))
        if ignored and name.casefold() in ignored:
            continue
        filtered_jobs.append(job)

    if not filtered_jobs:
        return "unknown"

    conclusions = [str(job.get("conclusion") or "").lower() for job in filtered_jobs]

    if all(conclusion in ("success", "skipped", "neutral") for conclusion in conclusions):
        return "success"

    if any(conclusion == "cancelled" for conclusion in conclusions):
        return "cancelled"

    if any(conclusion == "timed_out" for conclusion in conclusions):
        return "timed_out"

    if any(conclusion == "action_required" for conclusion in conclusions):
        return "action_required"

    return "failure"


# --------------------------------------------------------------------------- #
# Slack payload construction
# --------------------------------------------------------------------------- #


def determine_workflow_color_and_msg(
    completed_jobs: List[Dict[str, Any]],
    ignored_job_names: Optional[Set[str]] = None,
) -> Tuple[str, str]:
    ignored = ignored_job_names or set()

    filtered_jobs: List[Dict[str, Any]] = []
    for job in completed_jobs:
        name = normalise_job_name(str(job.get("name") or ""))
        if ignored and name.casefold() in ignored:
            continue
        filtered_jobs.append(job)

    if not filtered_jobs:
        return "warning", "Unknown:"

    conclusions = [str(job.get("conclusion") or "").lower() for job in filtered_jobs]

    if all(conclusion in ("success", "skipped", "neutral") for conclusion in conclusions):
        return "good", "Success:"

    if any(conclusion == "cancelled" for conclusion in conclusions):
        return "warning", "Cancelled:"

    if any(conclusion == "timed_out" for conclusion in conclusions):
        return "danger", "Timed out:"

    if any(conclusion == "action_required" for conclusion in conclusions):
        return "warning", "Action required:"

    return "danger", "Failed:"


def _should_include_jobs(include_jobs_mode: str, workflow_conclusion: str) -> bool:
    mode = (include_jobs_mode or "true").strip().lower()

    if mode == "false":
        return False

    if mode == "on-failure" and workflow_conclusion == "success":
        return False

    return True


def _job_status_icon(conclusion: str) -> str:
    conclusion = (conclusion or "").lower()

    if conclusion == "success":
        return "✓"

    if conclusion in ("cancelled", "skipped", "neutral"):
        return "⃠"

    if conclusion == "timed_out":
        return "⏱"

    if conclusion == "action_required":
        return "!"

    return "✗"


def _build_single_job_field(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conclusion = str(job.get("conclusion") or "").lower()
    raw_name = str(job.get("name") or "")
    name = normalise_job_name(raw_name)
    html_url = str(job.get("html_url") or "").strip()

    if not name or not html_url:
        return None

    icon = _job_status_icon(conclusion)

    started_at = parse_iso8601(job.get("started_at"))
    completed_at = parse_iso8601(job.get("completed_at"))

    if started_at and completed_at:
        job_duration = compute_duration(started_at, completed_at)
        value = f"{icon} <{html_url}|{name}> ({job_duration})"
    else:
        value = f"{icon} <{html_url}|{name}>"

    return {
        "title": "",
        "short": True,
        "value": value,
    }


def build_job_fields(
    completed_jobs: List[Dict[str, Any]],
    include_jobs_mode: str,
    workflow_conclusion: str,
    ignored_job_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    if not _should_include_jobs(include_jobs_mode, workflow_conclusion):
        return []

    name_field_pairs: List[Tuple[str, Dict[str, Any]]] = []
    ignored = ignored_job_names or set()

    for job in completed_jobs:
        raw_name = str(job.get("name") or "")
        name = normalise_job_name(raw_name)
        if not name:
            continue

        if ignored and name.casefold() in ignored:
            continue

        field = _build_single_job_field(job)
        if field is None:
            continue

        name_field_pairs.append((name, field))

    name_field_pairs.sort(key=lambda pair: pair[0].casefold())

    return [field for _name, field in name_field_pairs]


def _get_pull_requests(workflow_run: Dict[str, Any]) -> List[Dict[str, Any]]:
    pull_requests = workflow_run.get("pull_requests") or []
    if not isinstance(pull_requests, list):
        return []

    return [pr for pr in pull_requests if isinstance(pr, dict)]


def _is_internal_pull_request(pr: Dict[str, Any], repo_url: str) -> bool:
    base = pr.get("base") or {}
    if not isinstance(base, dict):
        return False

    base_repo = base.get("repo") or {}
    if not isinstance(base_repo, dict):
        return False

    base_repo_url = str(base_repo.get("url") or "")
    return bool(repo_url) and base_repo_url == repo_url


def _format_pull_request_segment(pr: Dict[str, Any], html_url: str) -> Optional[str]:
    if not html_url:
        return None

    number = pr.get("number")
    if number is None:
        return None

    head = pr.get("head") or {}
    base = pr.get("base") or {}

    if not isinstance(head, dict) or not isinstance(base, dict):
        return None

    head_ref = str(head.get("ref") or "").strip()
    base_ref = str(base.get("ref") or "").strip()

    link = f"{html_url}/pull/{number}"
    return f"<{link}|#{number}> from `{head_ref}` to `{base_ref}`"


def build_pull_request_string(workflow_run: Dict[str, Any]) -> str:
    repository = workflow_run.get("repository") or {}
    if not isinstance(repository, dict):
        return ""

    repo_url = str(repository.get("url") or "")
    html_url = str(repository.get("html_url") or "")

    segments: List[str] = []

    for pr in _get_pull_requests(workflow_run):
        if not _is_internal_pull_request(pr, repo_url):
            continue

        segment = _format_pull_request_segment(pr, html_url)
        if segment:
            segments.append(segment)

    return ", ".join(segments)


def _workflow_duration_string(workflow_run: Dict[str, Any]) -> str:
    created_at = parse_iso8601(workflow_run.get("created_at"))
    updated_at = parse_iso8601(workflow_run.get("updated_at"))

    if not (created_at and updated_at):
        return ""

    return compute_duration(created_at, updated_at)


def _extract_repo_context(workflow_run: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    repository = workflow_run.get("repository") or {}
    if not isinstance(repository, dict):
        repository = {}

    repo_full_name = str(repository.get("full_name") or "").strip()
    repo_html_url = str(repository.get("html_url") or "").strip()

    head_branch = str(workflow_run.get("head_branch") or "").strip()
    workflow_run_html_url = str(workflow_run.get("html_url") or "").strip()
    run_number = workflow_run.get("run_number")

    repo_url = f"<{repo_html_url}|*{repo_full_name}*>" if repo_html_url and repo_full_name else ""

    branch_url = (
        f"<{repo_html_url}/tree/{head_branch}|*{head_branch}*>"
        if repo_html_url and head_branch
        else head_branch
    )

    workflow_run_url = (
        f"<{workflow_run_html_url}|#{run_number}>"
        if workflow_run_html_url and run_number
        else ""
    )

    return repo_full_name, repo_html_url, repo_url, branch_url, workflow_run_url


def _build_status_string(
    workflow_msg: str,
    actor: str,
    event_name: str,
    branch_url: str,
    workflow_run: Dict[str, Any],
) -> str:
    default_status = (
        f"{workflow_msg} {actor}'s `{event_name}` on `{branch_url}`"
        if branch_url
        else f"{workflow_msg} {actor}'s `{event_name}`"
    )

    pull_requests_string = build_pull_request_string(workflow_run)
    if not pull_requests_string:
        return default_status

    return f"{workflow_msg} {actor}'s `pull_request` {pull_requests_string}"


def _build_details_text(
    workflow_name: str,
    workflow_run_url: str,
    workflow_duration: str,
) -> str:
    parts: List[str] = ["Workflow:"]

    if workflow_name:
        parts.append(workflow_name)

    if workflow_run_url:
        parts.append(workflow_run_url)

    details = " ".join(parts).strip()

    if workflow_duration:
        return f"{details} completed in `{workflow_duration}`"

    return f"{details} completed"


def _build_commit_message_text(
    head_commit_message: str,
    include_commit_message: bool,
) -> str:
    if not include_commit_message:
        return ""

    commit_subject = first_line(head_commit_message)
    if not commit_subject:
        return ""

    return f"Commit: {commit_subject}"


def _apply_slack_cosmetics(payload: Dict[str, Any]) -> None:
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


def build_slack_payload(
    workflow_run: Dict[str, Any],
    completed_jobs: List[Dict[str, Any]],
    include_jobs_mode: str,
    include_commit_message: bool,
    ignored_job_names: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    workflow_color, workflow_msg = determine_workflow_color_and_msg(
        completed_jobs,
        ignored_job_names=ignored_job_names,
    )

    workflow_conclusion_from_jobs = derive_workflow_conclusion_from_jobs(
        completed_jobs,
        ignored_job_names=ignored_job_names,
    )

    if workflow_conclusion_from_jobs != "unknown":
        workflow_conclusion = workflow_conclusion_from_jobs
    else:
        workflow_conclusion = get_workflow_conclusion(workflow_run)

    workflow_duration = _workflow_duration_string(workflow_run)

    (
        _repo_full_name,
        _repo_html_url,
        repo_url,
        branch_url,
        workflow_run_url,
    ) = _extract_repo_context(workflow_run)

    actor = os.environ.get("GITHUB_ACTOR", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    workflow_name = os.environ.get("GITHUB_WORKFLOW", "")

    status_string = _build_status_string(
        workflow_msg=workflow_msg,
        actor=actor,
        event_name=event_name,
        branch_url=branch_url,
        workflow_run=workflow_run,
    )

    details_text = _build_details_text(
        workflow_name=workflow_name,
        workflow_run_url=workflow_run_url,
        workflow_duration=workflow_duration,
    )

    head_commit = workflow_run.get("head_commit") or {}
    if not isinstance(head_commit, dict):
        head_commit = {}

    head_commit_message = str(head_commit.get("message") or "").strip()

    commit_message_text = _build_commit_message_text(
        head_commit_message=head_commit_message,
        include_commit_message=include_commit_message,
    )

    job_fields = build_job_fields(
        completed_jobs=completed_jobs,
        include_jobs_mode=include_jobs_mode,
        workflow_conclusion=workflow_conclusion,
        ignored_job_names=ignored_job_names,
    )

    text_lines: List[str] = [status_string, details_text]

    if commit_message_text:
        text_lines.append(commit_message_text)

    attachment: Dict[str, Any] = {
        "mrkdwn_in": ["text"],
        "color": workflow_color,
        "text": "\n".join(text_lines),
        "footer": repo_url,
        "footer_icon": "https://github.githubassets.com/favicon.ico",
        "fields": job_fields,
    }

    payload: Dict[str, Any] = {
        "attachments": [attachment],
    }

    _apply_slack_cosmetics(payload)

    return payload


def post_to_slack(webhook_url: str, payload: Dict[str, Any]) -> None:
    try:
        body = json.dumps(payload).encode("utf-8")
    except (TypeError, ValueError) as exc:
        error(f"Failed to serialise Slack payload as JSON: {exc}")

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
        error(f"Slack webhook returned HTTP {exc.code}: {exc.reason}")
    except URLError as exc:
        error(f"Failed to reach Slack webhook: {exc.reason}")
    except Exception as exc:  # pragma: no cover - defensive
        error(f"Unexpected error when calling Slack webhook: {exc}")

    if not (200 <= status < 300):
        error(f"Slack webhook returned HTTP {status}")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def should_send_notification(
    workflow_conclusion: str,
    results_setting: str,
) -> bool:
    results_setting = results_setting.strip().lower()

    if results_setting == "all":
        return True

    allowed = {item.strip() for item in results_setting.split(",") if item.strip()}

    if not allowed:
        return True

    return workflow_conclusion in allowed


def main() -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("slack_webhook_url")
    if not webhook_url:
        error("SLACK_WEBHOOK_URL environment variable is required.")

    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("ACTIONS_RUNTIME_TOKEN")

    if not repo or not run_id:
        error("GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API.")

    if not token:
        error("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is not set; cannot call GitHub API.")

    jobs_to_fetch_raw = os.environ.get("SEND_TO_SLACK_JOBS_TO_FETCH", str(DEFAULT_JOBS_PER_PAGE))
    try:
        jobs_to_fetch = int(jobs_to_fetch_raw)
    except ValueError:
        print(
            f"Warning: SEND_TO_SLACK_JOBS_TO_FETCH={jobs_to_fetch_raw!r} is not an integer; "
            f"defaulting to {DEFAULT_JOBS_PER_PAGE}.",
            file=sys.stderr,
        )
        jobs_to_fetch = DEFAULT_JOBS_PER_PAGE

    ignored_job_names = build_ignored_jobs()

    workflow_run, completed_jobs = fetch_run_and_jobs(
        repo=repo,
        run_id=run_id,
        token=token,
        jobs_per_page=jobs_to_fetch,
    )

    workflow_conclusion_from_jobs = derive_workflow_conclusion_from_jobs(
        completed_jobs,
        ignored_job_names=ignored_job_names,
    )

    if workflow_conclusion_from_jobs != "unknown":
        workflow_conclusion = workflow_conclusion_from_jobs
    else:
        workflow_conclusion = get_workflow_conclusion(workflow_run)

    results_setting = os.environ.get("SEND_TO_SLACK_RESULTS", "all")

    if not should_send_notification(workflow_conclusion, results_setting):
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
        ignored_job_names=ignored_job_names,
    )

    post_to_slack(webhook_url, payload)


if __name__ == "__main__":
    main()
