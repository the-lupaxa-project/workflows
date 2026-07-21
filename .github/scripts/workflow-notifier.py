#!/usr/bin/env python3
"""
Send GitHub Actions workflow status notifications to Slack.

This script is designed for use inside GitHub Actions. It fetches the current
workflow run and job details from the GitHub API, derives an overall workflow
result, builds a Slack webhook payload, and posts the notification.

The script is dependency-free and intentionally uses only the Python standard
library so it can run reliably on GitHub-hosted runners without bootstrapping
additional packages.
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple
from urllib.error import HTTPError, URLError


DEFAULT_JOBS_PER_PAGE = 100
MAX_JOBS_PER_PAGE = 100
DEFAULT_API_RETRIES = 3
DEFAULT_RETRY_BASE_SECONDS = 5
DEFAULT_RETRY_MAX_SECONDS = 60


DEFAULT_IGNORED_JOBS = {
    "check jobs status",
    "slack workflow status",
}

EMOJI_NOTIFY = "📣"
EMOJI_SUCCESS = "✅"
EMOJI_FAILURE = "❌"
EMOJI_CANCELLED = "🚫"
EMOJI_SKIPPED = "⏭️"
EMOJI_TIMEOUT = "⏱️"
EMOJI_WARNING = "⚠️"
EMOJI_NEUTRAL = "⚪"
EMOJI_UNKNOWN = "❔"
EMOJI_WORKFLOW = "🏃"
EMOJI_BRANCH = "🌿"
EMOJI_COMMIT = "🔖"
EMOJI_PR = "🔀"
EMOJI_REPO = "📦"


def error(message: str, *, code: int = 1) -> NoReturn:
    """Print a formatted error message and terminate the script."""
    print(f"{EMOJI_WARNING} ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def log(message: str = "") -> None:
    """Print a log message to stdout."""
    print(message, flush=True)


def env_value(name: str, default: str = "") -> str:
    """Read an environment variable as a string."""
    return os.environ.get(name, default)

def env_int(name: str, default: int) -> int:
    """Read an environment variable as an integer."""
    raw_value = env_value(name, str(default)).strip()

    try:
        return int(raw_value)
    except ValueError:
        print(
            f"{EMOJI_WARNING} Warning: {name}={raw_value!r} is not an integer; defaulting to {default}.",
            file=sys.stderr,
            flush=True,
        )
        return default


def retry_sleep_seconds(attempt: int) -> int:
    """Return the retry delay for an API attempt."""
    return min(DEFAULT_RETRY_MAX_SECONDS, (2 ** attempt) * DEFAULT_RETRY_BASE_SECONDS)


def first_line(value: str) -> str:
    """Return the first line of a string, stripped of surrounding whitespace."""
    return value.splitlines()[0].strip() if value.strip() else ""


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """Parse a GitHub-style ISO 8601 timestamp."""
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
    """Return a compact human-readable duration between two datetimes."""
    duration_seconds = max((end - start).total_seconds(), 0)
    delta = int(duration_seconds)

    days = delta // 86400
    delta -= days * 86400

    hours = delta // 3600
    delta -= hours * 3600

    minutes = delta // 60
    seconds = delta - minutes * 60

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
    """Extract the next-page URL from a GitHub API Link header."""
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


def github_api_headers(token: str) -> Dict[str, str]:
    """Build headers for a GitHub REST API request."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-send-to-slack",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def decode_http_error(exc: HTTPError) -> str:
    """Read and decode an HTTPError response body."""
    if not hasattr(exc, "read"):
        return ""

    return exc.read().decode("utf-8", errors="replace")


def parse_json_object(body_bytes: bytes, source: str) -> Dict[str, Any]:
    """Decode bytes as JSON and require a top-level object."""
    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode JSON from {source}: {exc}")

    if not isinstance(data, dict):
        error(f"GitHub API returned JSON from {source}, but top-level is not an object.")

    return data


def validate_http_status(status: int, body_bytes: bytes, source: str) -> None:
    """Validate an HTTP status code and report non-success response bodies."""
    if status == 200:
        return

    body = body_bytes.decode("utf-8", errors="replace")
    if body:
        print(f"GitHub API response body from {source}:", file=sys.stderr, flush=True)
        print(body, file=sys.stderr, flush=True)

    error(f"GitHub API returned HTTP {status} for {source}.")


def github_api_get_json(
    url: str,
    token: str,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Fetch JSON from the GitHub API and return the payload plus next URL."""
    retries = max(0, retries)

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=github_api_headers(token))

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.getcode()
                body_bytes = resp.read()
                link_header = resp.headers.get("Link", "")
        except HTTPError as exc:
            body = decode_http_error(exc)
            if exc.code in {403, 429, 500, 502, 503, 504} and attempt < retries:
                sleep_for = retry_sleep_seconds(attempt)
                print(
                    f"{EMOJI_WARNING} GitHub API returned HTTP {exc.code} for {url}; retrying in {sleep_for}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(sleep_for)
                continue

            if body:
                print(body, file=sys.stderr, flush=True)
            error(f"GitHub API returned HTTP {exc.code} for {url}: {exc.reason}")
        except URLError as exc:
            if attempt < retries:
                sleep_for = retry_sleep_seconds(attempt)
                print(
                    f"{EMOJI_WARNING} Failed to reach GitHub API at {url}: {exc.reason}; retrying in {sleep_for}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(sleep_for)
                continue

            error(f"Failed to reach GitHub API at {url}: {exc.reason}")
        except Exception as exc:
            error(f"Unexpected error when calling GitHub API at {url}: {exc}")

        validate_http_status(status, body_bytes, url)
        return parse_json_object(body_bytes, url), parse_next_link(link_header)

    error(f"GitHub API request failed after retries: {url}")


def fetch_json_with_next(
    url: str,
    token: str,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Compatibility wrapper for paginated GitHub API reads."""
    return github_api_get_json(url, token, retries=retries)


def fetch_json(
    url: str,
    token: str,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> Dict[str, Any]:
    """Fetch a single JSON object from the GitHub API."""
    data, _next_url = github_api_get_json(url, token, retries=retries)
    return data


def normalise_job_name(raw: str) -> str:
    """Normalise a job name for display and ignore-list matching."""
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]

    return raw.strip()


def parse_ignored_jobs(raw: str) -> Set[str]:
    """Parse comma-separated job names into a case-insensitive ignore set."""
    ignored: Set[str] = set()

    for part in raw.split(","):
        name = normalise_job_name(part)
        if name:
            ignored.add(name.casefold())

    return ignored


def build_ignored_jobs() -> Set[str]:
    """Build the full set of ignored jobs from defaults and environment input."""
    ignored = set(DEFAULT_IGNORED_JOBS)

    raw_ignored_jobs = env_value("SEND_TO_SLACK_IGNORE_JOBS")
    if raw_ignored_jobs.strip():
        ignored.update(parse_ignored_jobs(raw_ignored_jobs))

    return ignored


def workflow_status_emoji(conclusion: str) -> str:
    """Return an emoji representing a workflow conclusion."""
    conclusion = conclusion.lower()

    if conclusion == "success":
        return EMOJI_SUCCESS
    if conclusion == "failure":
        return EMOJI_FAILURE
    if conclusion == "cancelled":
        return EMOJI_CANCELLED
    if conclusion == "timed_out":
        return EMOJI_TIMEOUT
    if conclusion == "action_required":
        return EMOJI_WARNING
    if conclusion in ("skipped", "neutral"):
        return EMOJI_NEUTRAL

    return EMOJI_UNKNOWN


def normalise_jobs_per_page(raw_value: str) -> int:
    """Parse and clamp the requested GitHub jobs page size."""
    try:
        jobs_per_page = int(raw_value)
    except ValueError:
        print(
            f"{EMOJI_WARNING} Warning: SEND_TO_SLACK_JOBS_TO_FETCH={raw_value!r} "
            f"is not an integer; defaulting to {DEFAULT_JOBS_PER_PAGE}.",
            file=sys.stderr,
            flush=True,
        )
        return DEFAULT_JOBS_PER_PAGE

    if jobs_per_page <= 0:
        return DEFAULT_JOBS_PER_PAGE

    return min(jobs_per_page, MAX_JOBS_PER_PAGE)


def completed_only(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only completed GitHub Actions jobs."""
    return [job for job in jobs if str(job.get("status") or "").lower() == "completed"]


def fetch_jobs(
    jobs_url: str,
    token: str,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> List[Dict[str, Any]]:
    """Fetch all workflow jobs from a paginated GitHub API endpoint."""
    all_jobs: List[Dict[str, Any]] = []
    url: Optional[str] = jobs_url

    while url:
        jobs_data, next_url = github_api_get_json(url, token, retries=retries)

        jobs_raw = jobs_data.get("jobs", [])
        if isinstance(jobs_raw, list):
            all_jobs.extend(job for job in jobs_raw if isinstance(job, dict))

        log(f"{EMOJI_WORKFLOW} Loaded {len(all_jobs)} workflow jobs so far")
        url = next_url

    return all_jobs


def warn_if_no_completed_jobs(completed_jobs: List[Dict[str, Any]]) -> None:
    """Warn when no completed jobs were found for the workflow run."""
    if completed_jobs:
        return

    print(
        f"{EMOJI_WARNING} Warning: No completed jobs found for this workflow run. "
        "Slack notification will contain no job fields.",
        file=sys.stderr,
        flush=True,
    )


def fetch_run_and_jobs(
    repo: str,
    run_id: str,
    token: str,
    jobs_per_page: int,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Fetch the workflow run payload and completed job list."""
    jobs_per_page = max(1, min(jobs_per_page, MAX_JOBS_PER_PAGE))
    base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"

    run = fetch_json(base, token, retries=retries)
    jobs = fetch_jobs(f"{base}/jobs?per_page={jobs_per_page}", token, retries=retries)
    completed_jobs = completed_only(jobs)

    warn_if_no_completed_jobs(completed_jobs)

    return run, completed_jobs


def get_workflow_conclusion(workflow_run: Dict[str, Any]) -> str:
    """Return the workflow run conclusion, falling back to status."""
    conclusion = str(workflow_run.get("conclusion") or "").strip().lower()
    status = str(workflow_run.get("status") or "").strip().lower()

    if conclusion:
        return conclusion
    if status:
        return status

    return "unknown"


def filtered_jobs(
    completed_jobs: List[Dict[str, Any]],
    ignored_job_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """Return completed jobs after applying the ignored-job set."""
    ignored = ignored_job_names or set()
    selected: List[Dict[str, Any]] = []

    for job in completed_jobs:
        name = normalise_job_name(str(job.get("name") or ""))
        if ignored and name.casefold() in ignored:
            continue
        selected.append(job)

    return selected


def job_conclusions(jobs: List[Dict[str, Any]]) -> List[str]:
    """Return lower-cased conclusions for a list of jobs."""
    return [str(job.get("conclusion") or "").lower() for job in jobs]


def derive_workflow_conclusion_from_jobs(
    completed_jobs: List[Dict[str, Any]],
    ignored_job_names: Optional[Set[str]] = None,
) -> str:
    """Derive the overall workflow conclusion from completed job conclusions."""
    selected_jobs = filtered_jobs(completed_jobs, ignored_job_names)

    if not selected_jobs:
        return "unknown"

    conclusions = job_conclusions(selected_jobs)

    if all(conclusion in ("success", "skipped", "neutral") for conclusion in conclusions):
        return "success"

    if any(conclusion == "cancelled" for conclusion in conclusions):
        return "cancelled"

    if any(conclusion == "timed_out" for conclusion in conclusions):
        return "timed_out"

    if any(conclusion == "action_required" for conclusion in conclusions):
        return "action_required"

    return "failure"


def determine_workflow_color_and_msg(
    completed_jobs: List[Dict[str, Any]],
    ignored_job_names: Optional[Set[str]] = None,
) -> Tuple[str, str]:
    """Return the Slack attachment colour and leading status message."""
    selected_jobs = filtered_jobs(completed_jobs, ignored_job_names)

    if not selected_jobs:
        return "warning", f"{EMOJI_UNKNOWN} Unknown:"

    conclusion = derive_workflow_conclusion_from_jobs(selected_jobs)

    if conclusion == "success":
        return "good", f"{EMOJI_SUCCESS} Success:"
    if conclusion == "cancelled":
        return "warning", f"{EMOJI_CANCELLED} Cancelled:"
    if conclusion == "timed_out":
        return "danger", f"{EMOJI_TIMEOUT} Timed out:"
    if conclusion == "action_required":
        return "warning", f"{EMOJI_WARNING} Action required:"

    return "danger", f"{EMOJI_FAILURE} Failed:"


def should_include_jobs(include_jobs_mode: str, workflow_conclusion: str) -> bool:
    """Return whether per-job Slack fields should be included."""
    mode = (include_jobs_mode or "true").strip().lower()

    if mode == "false":
        return False

    if mode == "on-failure" and workflow_conclusion == "success":
        return False

    return True


def job_status_icon(conclusion: str) -> str:
    """Return an emoji representing a job conclusion."""
    conclusion = (conclusion or "").lower()

    if conclusion == "success":
        return EMOJI_SUCCESS
    if conclusion == "failure":
        return EMOJI_FAILURE
    if conclusion == "timed_out":
        return EMOJI_TIMEOUT
    if conclusion == "cancelled":
        return EMOJI_CANCELLED
    if conclusion == "skipped":
        return EMOJI_SKIPPED
    if conclusion == "neutral":
        return EMOJI_NEUTRAL
    if conclusion == "action_required":
        return EMOJI_WARNING

    return EMOJI_UNKNOWN


def job_duration(job: Dict[str, Any]) -> str:
    """Return the duration for a completed job, or an empty string."""
    started_at = parse_iso8601(job.get("started_at"))
    completed_at = parse_iso8601(job.get("completed_at"))

    if started_at and completed_at:
        return compute_duration(started_at, completed_at)

    return ""


def build_single_job_field(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a Slack attachment field for one workflow job."""
    conclusion = str(job.get("conclusion") or "").lower()
    name = normalise_job_name(str(job.get("name") or ""))
    html_url = str(job.get("html_url") or "").strip()

    if not name or not html_url:
        return None

    icon = job_status_icon(conclusion)
    duration = job_duration(job)

    if duration:
        value = f"{icon} <{html_url}|{name}> ({duration})"
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
    """Build sorted Slack attachment fields for completed jobs."""
    if not should_include_jobs(include_jobs_mode, workflow_conclusion):
        return []

    name_field_pairs: List[Tuple[str, Dict[str, Any]]] = []

    for job in filtered_jobs(completed_jobs, ignored_job_names):
        name = normalise_job_name(str(job.get("name") or ""))
        if not name:
            continue

        field = build_single_job_field(job)
        if field is None:
            continue

        name_field_pairs.append((name, field))

    name_field_pairs.sort(key=lambda pair: pair[0].casefold())

    return [field for _name, field in name_field_pairs]


def get_pull_requests(workflow_run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return pull request objects from a workflow run payload."""
    pull_requests = workflow_run.get("pull_requests") or []
    if not isinstance(pull_requests, list):
        return []

    return [pr for pr in pull_requests if isinstance(pr, dict)]


def is_internal_pull_request(pr: Dict[str, Any], repo_url: str) -> bool:
    """Return whether a pull request targets the current repository."""
    base = pr.get("base") or {}
    if not isinstance(base, dict):
        return False

    base_repo = base.get("repo") or {}
    if not isinstance(base_repo, dict):
        return False

    base_repo_url = str(base_repo.get("url") or "")

    return bool(repo_url) and base_repo_url == repo_url


def format_pull_request_segment(pr: Dict[str, Any], html_url: str) -> Optional[str]:
    """Format a pull request segment for Slack mrkdwn."""
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
    """Build a Slack-friendly pull request summary string."""
    repository = workflow_run.get("repository") or {}
    if not isinstance(repository, dict):
        return ""

    repo_url = str(repository.get("url") or "")
    html_url = str(repository.get("html_url") or "")

    segments: List[str] = []

    for pr in get_pull_requests(workflow_run):
        if not is_internal_pull_request(pr, repo_url):
            continue

        segment = format_pull_request_segment(pr, html_url)
        if segment:
            segments.append(segment)

    return ", ".join(segments)


def workflow_duration_string(workflow_run: Dict[str, Any]) -> str:
    """Return the workflow run duration, or an empty string."""
    created_at = parse_iso8601(workflow_run.get("created_at"))
    updated_at = parse_iso8601(workflow_run.get("updated_at"))

    if not (created_at and updated_at):
        return ""

    return compute_duration(created_at, updated_at)


def extract_repository(workflow_run: Dict[str, Any]) -> Dict[str, Any]:
    """Return the workflow run repository object."""
    repository = workflow_run.get("repository") or {}

    return repository if isinstance(repository, dict) else {}


def build_repo_footer(repository: Dict[str, Any]) -> str:
    """Build the Slack attachment footer text for the repository."""
    repo_full_name = str(repository.get("full_name") or "").strip()
    repo_html_url = str(repository.get("html_url") or "").strip()

    if repo_html_url and repo_full_name:
        return f"<{repo_html_url}|{EMOJI_REPO} *{repo_full_name}*>"

    return ""


def build_branch_link(workflow_run: Dict[str, Any], repository: Dict[str, Any]) -> str:
    """Build a Slack link for the workflow branch."""
    repo_html_url = str(repository.get("html_url") or "").strip()
    head_branch = str(workflow_run.get("head_branch") or "").strip()

    if repo_html_url and head_branch:
        return f"<{repo_html_url}/tree/{head_branch}|{EMOJI_BRANCH} *{head_branch}*>"

    return head_branch


def build_workflow_run_link(workflow_run: Dict[str, Any]) -> str:
    """Build a Slack link for the workflow run."""
    workflow_run_html_url = str(workflow_run.get("html_url") or "").strip()
    run_number = workflow_run.get("run_number")

    if workflow_run_html_url and run_number:
        return f"<{workflow_run_html_url}|#{run_number}>"

    return ""


def build_status_string(
    workflow_msg: str,
    actor: str,
    event_name: str,
    branch_url: str,
    workflow_run: Dict[str, Any],
) -> str:
    """Build the first status line for the Slack notification."""
    default_status = (
        f"{workflow_msg} {actor}'s `{event_name}` on {branch_url}"
        if branch_url
        else f"{workflow_msg} {actor}'s `{event_name}`"
    )

    pull_requests_string = build_pull_request_string(workflow_run)
    if not pull_requests_string:
        return default_status

    return f"{workflow_msg} {actor}'s `{event_name}` {EMOJI_PR} {pull_requests_string}"


def build_details_text(
    workflow_name: str,
    workflow_run_url: str,
    workflow_duration: str,
) -> str:
    """Build the workflow details line for the Slack notification."""
    parts: List[str] = [f"{EMOJI_WORKFLOW} Workflow:"]

    if workflow_name:
        parts.append(workflow_name)

    if workflow_run_url:
        parts.append(workflow_run_url)

    details = " ".join(parts).strip()

    if workflow_duration:
        return f"{details} completed in `{workflow_duration}`"

    return f"{details} completed"


def build_commit_message_text(
    head_commit_message: str,
    include_commit_message: bool,
) -> str:
    """Build the optional commit message line for the Slack notification."""
    if not include_commit_message:
        return ""

    commit_subject = first_line(head_commit_message)
    if not commit_subject:
        return ""

    return f"{EMOJI_COMMIT} Commit: {commit_subject}"


def slack_cosmetic_value(primary_name: str, fallback_name: str) -> str:
    """Read a Slack cosmetic setting from preferred and fallback env vars."""
    return env_value(primary_name) or env_value(fallback_name)


def apply_slack_cosmetics(payload: Dict[str, Any]) -> None:
    """Apply optional Slack channel, username and icon customisations."""
    channel = slack_cosmetic_value("SEND_TO_SLACK_CHANNEL", "SLACK_CHANNEL")
    if channel:
        payload["channel"] = channel

    username = slack_cosmetic_value("SEND_TO_SLACK_NAME", "SLACK_NAME")
    if username:
        payload["username"] = username

    icon_emoji = slack_cosmetic_value("SEND_TO_SLACK_ICON_EMOJI", "SLACK_ICON_EMOJI")
    if icon_emoji:
        payload["icon_emoji"] = icon_emoji

    icon_url = slack_cosmetic_value("SEND_TO_SLACK_ICON_URL", "SLACK_ICON_URL")
    if icon_url:
        payload["icon_url"] = icon_url


def head_commit_message(workflow_run: Dict[str, Any]) -> str:
    """Return the head commit message from the workflow run payload."""
    head_commit = workflow_run.get("head_commit") or {}
    if not isinstance(head_commit, dict):
        return ""

    return str(head_commit.get("message") or "").strip()


def resolve_workflow_conclusion(
    workflow_run: Dict[str, Any],
    completed_jobs: List[Dict[str, Any]],
    ignored_job_names: Optional[Set[str]] = None,
) -> str:
    """Resolve the workflow conclusion using jobs first, then run metadata."""
    workflow_conclusion_from_jobs = derive_workflow_conclusion_from_jobs(
        completed_jobs,
        ignored_job_names=ignored_job_names,
    )

    if workflow_conclusion_from_jobs != "unknown":
        return workflow_conclusion_from_jobs

    return get_workflow_conclusion(workflow_run)


def build_attachment_text(
    workflow_run: Dict[str, Any],
    workflow_msg: str,
    include_commit_message: bool,
) -> str:
    """Build the multi-line Slack attachment text body."""
    repository = extract_repository(workflow_run)
    branch_url = build_branch_link(workflow_run, repository)
    workflow_run_url = build_workflow_run_link(workflow_run)
    workflow_duration = workflow_duration_string(workflow_run)

    actor = env_value("GITHUB_ACTOR")
    event_name = env_value("GITHUB_EVENT_NAME")
    workflow_name = env_value("GITHUB_WORKFLOW")

    lines = [
        build_status_string(workflow_msg, actor, event_name, branch_url, workflow_run),
        build_details_text(workflow_name, workflow_run_url, workflow_duration),
    ]

    commit_message = build_commit_message_text(
        head_commit_message(workflow_run),
        include_commit_message,
    )
    if commit_message:
        lines.append(commit_message)

    return "\n".join(lines)


def build_slack_attachment(
    workflow_run: Dict[str, Any],
    completed_jobs: List[Dict[str, Any]],
    include_jobs_mode: str,
    include_commit_message: bool,
    ignored_job_names: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Build the primary Slack attachment."""
    workflow_color, workflow_msg = determine_workflow_color_and_msg(
        completed_jobs,
        ignored_job_names=ignored_job_names,
    )
    workflow_conclusion = resolve_workflow_conclusion(
        workflow_run,
        completed_jobs,
        ignored_job_names=ignored_job_names,
    )

    return {
        "mrkdwn_in": ["text", "fields"],
        "color": workflow_color,
        "text": build_attachment_text(workflow_run, workflow_msg, include_commit_message),
        "footer": build_repo_footer(extract_repository(workflow_run)),
        "footer_icon": "https://github.githubassets.com/favicon.ico",
        "fields": build_job_fields(
            completed_jobs=completed_jobs,
            include_jobs_mode=include_jobs_mode,
            workflow_conclusion=workflow_conclusion,
            ignored_job_names=ignored_job_names,
        ),
    }


def build_slack_payload(
    workflow_run: Dict[str, Any],
    completed_jobs: List[Dict[str, Any]],
    include_jobs_mode: str,
    include_commit_message: bool,
    ignored_job_names: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Build the complete Slack webhook payload."""
    payload: Dict[str, Any] = {
        "text": f"{EMOJI_NOTIFY} GitHub Actions workflow status",
        "attachments": [
            build_slack_attachment(
                workflow_run=workflow_run,
                completed_jobs=completed_jobs,
                include_jobs_mode=include_jobs_mode,
                include_commit_message=include_commit_message,
                ignored_job_names=ignored_job_names,
            )
        ],
    }

    apply_slack_cosmetics(payload)

    return payload


def serialise_slack_payload(payload: Dict[str, Any]) -> bytes:
    """Serialise a Slack payload to UTF-8 JSON bytes."""
    try:
        return json.dumps(payload).encode("utf-8")
    except (TypeError, ValueError) as exc:
        error(f"Failed to serialise Slack payload as JSON: {exc}")


def post_to_slack(webhook_url: str, payload: Dict[str, Any]) -> None:
    """Post a payload to a Slack incoming webhook."""
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        webhook_url,
        data=serialise_slack_payload(payload),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            _ = resp.read()
    except HTTPError as exc:
        resp_body = decode_http_error(exc)
        if resp_body:
            print(resp_body, file=sys.stderr, flush=True)
        error(f"Slack webhook returned HTTP {exc.code}: {exc.reason}")
    except URLError as exc:
        error(f"Failed to reach Slack webhook: {exc.reason}")
    except Exception as exc:
        error(f"Unexpected error when calling Slack webhook: {exc}")

    if not (200 <= status < 300):
        error(f"Slack webhook returned HTTP {status}")


def should_send_notification(
    workflow_conclusion: str,
    results_setting: str,
) -> bool:
    """Return whether the workflow conclusion matches the configured results."""
    results_setting = results_setting.strip().lower()

    if results_setting == "all":
        return True

    allowed = {item.strip() for item in results_setting.split(",") if item.strip()}

    if not allowed:
        return True

    return workflow_conclusion in allowed


def github_token_from_env() -> str:
    """Return the first available GitHub API token."""
    return (
        env_value("GITHUB_TOKEN")
        or env_value("GH_TOKEN")
        or env_value("ACTIONS_RUNTIME_TOKEN")
    )


def required_context_from_env() -> Tuple[str, str, str, str]:
    """Read and validate required runtime context from environment variables."""
    webhook_url = env_value("SLACK_WEBHOOK_URL") or env_value("slack_webhook_url")
    if not webhook_url:
        error("SLACK_WEBHOOK_URL environment variable is required.")

    repo = env_value("GITHUB_REPOSITORY")
    run_id = env_value("GITHUB_RUN_ID")
    token = github_token_from_env()

    if not repo or not run_id:
        error("GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API.")

    if not token:
        error("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is not set; cannot call GitHub API.")

    return webhook_url, repo, run_id, token


def include_commit_message_from_env() -> bool:
    """Return whether commit messages should be included in Slack output."""
    raw_value = env_value("SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE", "true")

    return raw_value.strip().lower() == "true"


def skip_notification_message(workflow_conclusion: str, results_setting: str) -> None:
    """Print a message explaining why the Slack notification was skipped."""
    print(
        f"{EMOJI_SKIPPED} Workflow conclusion '{workflow_conclusion}' not in "
        f"SEND_TO_SLACK_RESULTS={results_setting!r}; skipping Slack notification.",
        file=sys.stderr,
        flush=True,
    )


def main() -> None:
    """Run the Slack workflow status notifier."""
    webhook_url, repo, run_id, token = required_context_from_env()

    jobs_to_fetch = normalise_jobs_per_page(
        env_value("SEND_TO_SLACK_JOBS_TO_FETCH", str(DEFAULT_JOBS_PER_PAGE))
    )
    ignored_job_names = build_ignored_jobs()
    api_retries = env_int("SEND_TO_SLACK_API_RETRIES", DEFAULT_API_RETRIES)

    workflow_run, completed_jobs = fetch_run_and_jobs(
        repo=repo,
        run_id=run_id,
        token=token,
        jobs_per_page=jobs_to_fetch,
        retries=api_retries,
    )

    workflow_conclusion = resolve_workflow_conclusion(
        workflow_run,
        completed_jobs,
        ignored_job_names=ignored_job_names,
    )

    results_setting = env_value("SEND_TO_SLACK_RESULTS", "all")

    if not should_send_notification(workflow_conclusion, results_setting):
        skip_notification_message(workflow_conclusion, results_setting)
        return

    log(
        f"{EMOJI_NOTIFY} Sending Slack notification for workflow conclusion: "
        f"{workflow_status_emoji(workflow_conclusion)} {workflow_conclusion}"
    )

    payload = build_slack_payload(
        workflow_run=workflow_run,
        completed_jobs=completed_jobs,
        include_jobs_mode=env_value("SEND_TO_SLACK_INCLUDE_JOBS", "true"),
        include_commit_message=include_commit_message_from_env(),
        ignored_job_names=ignored_job_names,
    )

    post_to_slack(webhook_url, payload)

    log(f"{EMOJI_SUCCESS} Slack notification sent")


if __name__ == "__main__":
    main()
