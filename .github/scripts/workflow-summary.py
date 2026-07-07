#!/usr/bin/env python3
"""
Generate a GitHub Actions workflow summary.

This script reads job results for the current GitHub Actions workflow run,
groups jobs by conclusion, and writes a Markdown summary to both the GitHub
step summary and an artifact-ready Markdown file.

The script normally fetches job information from the GitHub Actions API using
environment variables provided by GitHub Actions. For local testing, a JSON
file can be supplied as the only command-line argument.
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Set, TextIO, Tuple, cast
from urllib.error import HTTPError, URLError


JobRecord = Tuple[str, str, str, str]
JobBuckets = Dict[str, List[Tuple[str, str]]]

DEFAULT_JOBS_PER_PAGE = 100
MAX_JOBS_PER_PAGE = 100
DEFAULT_API_RETRIES = 3
DEFAULT_RETRY_BASE_SECONDS = 5
DEFAULT_RETRY_MAX_SECONDS = 60


EMOJI_SUMMARY = "📊"
EMOJI_SUCCESS = "✅"
EMOJI_FAILURE = "❌"
EMOJI_TIMEOUT = "⏱️"
EMOJI_CANCELLED = "🚫"
EMOJI_SKIPPED = "⏭️"
EMOJI_NEUTRAL = "⚪"
EMOJI_WARNING = "⚠️"
EMOJI_STALE = "🕰️"
EMOJI_RUNNING = "🔄"
EMOJI_OTHER = "❔"
EMOJI_METADATA = "ℹ️"
EMOJI_WORKFLOW = "🏃"
EMOJI_WORKFLOW_FILE = "📄"
EMOJI_REPO = "📦"
EMOJI_RUN = "🏃"
EMOJI_ATTEMPT = "🔁"
EMOJI_EVENT = "⚡"
EMOJI_ACTOR = "👤"
EMOJI_TRIGGERING_ACTOR = "👥"
EMOJI_BRANCH = "🌿"
EMOJI_COMMIT = "🔖"
EMOJI_PR = "🔀"
EMOJI_GENERATED = "🕒"

JOB_BUCKET_ORDER = (
    "success",
    "failure",
    "timed_out",
    "cancelled",
    "skipped",
    "neutral",
    "action_required",
    "stale",
    "not_completed",
    "other",
)

JOB_SECTION_ORDER = (
    "failure",
    "timed_out",
    "cancelled",
    "not_completed",
    "action_required",
    "stale",
    "neutral",
    "skipped",
    "other",
    "success",
)

STATUS_LABELS = {
    "success": f"{EMOJI_SUCCESS} Successful",
    "failure": f"{EMOJI_FAILURE} Failed",
    "timed_out": f"{EMOJI_TIMEOUT} Timed out",
    "cancelled": f"{EMOJI_CANCELLED} Cancelled",
    "skipped": f"{EMOJI_SKIPPED} Skipped",
    "neutral": f"{EMOJI_NEUTRAL} Neutral",
    "action_required": f"{EMOJI_WARNING} Action required",
    "stale": f"{EMOJI_STALE} Stale",
    "not_completed": f"{EMOJI_RUNNING} Not completed",
    "other": f"{EMOJI_OTHER} Other",
}

SECTION_TITLES = {
    "success": f"{EMOJI_SUCCESS} Successful jobs",
    "failure": f"{EMOJI_FAILURE} Failed jobs",
    "timed_out": f"{EMOJI_TIMEOUT} Timed out jobs",
    "cancelled": f"{EMOJI_CANCELLED} Cancelled jobs",
    "skipped": f"{EMOJI_SKIPPED} Skipped jobs",
    "neutral": f"{EMOJI_NEUTRAL} Neutral jobs",
    "action_required": f"{EMOJI_WARNING} Action required jobs",
    "stale": f"{EMOJI_STALE} Stale jobs",
    "not_completed": f"{EMOJI_RUNNING} Not completed jobs",
    "other": f"{EMOJI_OTHER} Other statuses",
}


def error(message: str, *, code: int = 1) -> NoReturn:
    """Print a formatted error message and terminate the script."""
    print(f"{EMOJI_WARNING} ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def ordinal_suffix(day: int) -> str:
    """Return the ordinal suffix for a day of the month as HTML superscript."""
    if day in (1, 21, 31):
        suffix = "st"
    elif day in (2, 22):
        suffix = "nd"
    elif day in (3, 23):
        suffix = "rd"
    else:
        suffix = "th"

    return f"<sup>{suffix}</sup>"


def build_human_timestamp() -> str:
    """Return the current UTC time in a human-readable display format."""
    now = datetime.now(timezone.utc)
    day = now.day

    return (
        f"{now.strftime('%A')} "
        f"{day}{ordinal_suffix(day)} "
        f"{now.strftime('%B')} "
        f"{now.strftime('%Y')} "
        f"{now.strftime('%H:%M:%S')}"
    )


def md_table_value(value: str) -> str:
    """Escape a value so it can be safely rendered inside a Markdown table."""
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("|", "\\|")
    value = value.replace("\r", " ")
    value = value.replace("\n", " ")

    return value.strip()


def slugify(value: str, *, fallback: str = "unknown") -> str:
    """Convert a string into a filesystem-friendly slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-._")

    return value or fallback


def workflow_file_name_from_ref(workflow_ref: str) -> str:
    """Extract the workflow filename stem from a GitHub workflow ref."""
    if not workflow_ref:
        return ""

    path_part = workflow_ref.split("@", 1)[0]
    filename = path_part.rsplit("/", 1)[-1]

    return filename.rsplit(".", 1)[0]


def default_summary_filename() -> str:
    """Build the default Markdown summary artifact path."""
    workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF", "")
    workflow_file = workflow_file_name_from_ref(workflow_ref)
    workflow_name = os.environ.get("GITHUB_WORKFLOW", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")

    name_parts = [
        "workflow-summary",
        slugify(workflow_file or workflow_name),
        slugify(run_id),
        f"attempt-{slugify(run_attempt)}",
    ]

    filename = "-".join(part for part in name_parts if part) + ".md"
    output_dir = os.environ.get("RUNNER_TEMP", "").strip() or os.getcwd()

    return str(Path(output_dir) / filename)

def short_sha(sha: str) -> str:
    """Return the short seven-character version of a Git commit SHA."""
    return sha[:7] if sha else ""


def normalise_result(raw_result: str) -> str:
    """Normalise a GitHub Actions job result into an internal bucket key."""
    return str(raw_result or "unknown").strip().lower().replace("-", "_")


def make_link(label: str, url: str) -> str:
    """Return a Markdown link when both label and URL are available."""
    if not label or not url:
        return md_table_value(label or url)

    return f"[{md_table_value(label)}]({url})"


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


def status_label(key: str) -> str:
    """Return the display label for a job result bucket."""
    return STATUS_LABELS.get(key, f"{EMOJI_OTHER} {key}")


def section_title(key: str) -> str:
    """Return the Markdown section title for a job result bucket."""
    return SECTION_TITLES.get(key, key)


def github_token_from_env() -> str:
    """Return the first supported GitHub API token found in the environment."""
    return (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("ACTIONS_RUNTIME_TOKEN")
        or ""
    )


def get_github_context_from_env() -> Tuple[str, str, str]:
    """Read and validate the GitHub API context from environment variables."""
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    token = github_token_from_env()

    if not repo or not run_id:
        error("GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API.")

    if not token:
        error("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is not set; cannot call GitHub API.")

    return repo, run_id, token


def env_int(name: str, default: int) -> int:
    """Read an environment variable as an integer."""
    raw_value = os.environ.get(name, str(default)).strip()

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


def github_api_headers(token: str) -> Dict[str, str]:
    """Build the HTTP headers required for GitHub API requests."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-workflow-summary",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def decode_http_error(exc: HTTPError) -> str:
    """Read and decode the response body from a GitHub API HTTPError."""
    if not hasattr(exc, "read"):
        return ""

    return exc.read().decode("utf-8", errors="replace")


def github_api_get_json(
    url: str,
    token: str,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Fetch JSON from the GitHub API and return the parsed payload and next URL."""
    retries = max(0, retries)

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=github_api_headers(token))

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                status = response.getcode()
                body_bytes = response.read()
                link_header = response.headers.get("Link", "")
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

        validate_github_status(status, body_bytes, url)
        data = parse_github_json(body_bytes, url)

        return data, parse_next_link(link_header)

    error(f"GitHub API request failed after retries: {url}")


def validate_github_status(status: int, body_bytes: bytes, source: str) -> None:
    """Validate a GitHub API HTTP status code."""
    if status == 200:
        return

    body = body_bytes.decode("utf-8", errors="replace")
    if body:
        print(f"GitHub API response body from {source}:", file=sys.stderr, flush=True)
        print(body, file=sys.stderr, flush=True)

    error(f"GitHub API returned HTTP {status} for {source}.")


def parse_github_json(body_bytes: bytes, source: str) -> Dict[str, Any]:
    """Decode a GitHub API response body as a JSON object."""
    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode GitHub API JSON from {source}: {exc}")

    if not isinstance(data, dict):
        error(f"GitHub API returned JSON from {source}, but the top-level structure is not an object.")

    return data


def fetch_jobs_page(
    url: str,
    token: str,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Fetch one page of workflow jobs from the GitHub Actions API."""
    data, next_url = github_api_get_json(url, token, retries=retries)
    jobs = data.get("jobs")

    if not isinstance(jobs, list):
        error("GitHub jobs API response did not contain a 'jobs' list.")

    return [job for job in jobs if isinstance(job, dict)], next_url


def fetch_jobs_json(
    repo: str,
    run_id: str,
    token: str,
    *,
    jobs_per_page: int = DEFAULT_JOBS_PER_PAGE,
    retries: int = DEFAULT_API_RETRIES,
) -> Dict[str, Any]:
    """Fetch all jobs for a GitHub Actions workflow run."""
    jobs_per_page = max(1, min(jobs_per_page, MAX_JOBS_PER_PAGE))
    url: Optional[str] = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page={jobs_per_page}"
    all_jobs: List[Dict[str, Any]] = []

    while url:
        jobs, url = fetch_jobs_page(url, token, retries=retries)
        all_jobs.extend(jobs)
        print(f"{EMOJI_WORKFLOW} Loaded {len(all_jobs)} workflow jobs so far", flush=True)

    return {
        "total_count": len(all_jobs),
        "jobs": all_jobs,
    }


def maybe_set_commit_message_env(
    repo: str,
    run_id: str,
    token: str,
    *,
    retries: int = DEFAULT_API_RETRIES,
) -> None:
    """Populate GITHUB_COMMIT_MESSAGE from the workflow run when available."""
    run_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"

    try:
        data, _ = github_api_get_json(run_url, token, retries=retries)
    except SystemExit:
        return

    head_commit = data.get("head_commit") or {}
    if not isinstance(head_commit, dict):
        return

    message = str(head_commit.get("message") or "").strip()
    if message:
        os.environ["GITHUB_COMMIT_MESSAGE"] = message


def fetch_jobs_json_from_api() -> Dict[str, Any]:
    """Fetch workflow job data for the current GitHub Actions run."""
    repo, run_id, token = get_github_context_from_env()
    jobs_per_page = env_int("WORKFLOW_SUMMARY_JOBS_TO_FETCH", DEFAULT_JOBS_PER_PAGE)
    api_retries = env_int("WORKFLOW_SUMMARY_API_RETRIES", DEFAULT_API_RETRIES)

    jobs_data = fetch_jobs_json(
        repo,
        run_id,
        token,
        jobs_per_page=jobs_per_page,
        retries=api_retries,
    )
    maybe_set_commit_message_env(repo, run_id, token, retries=api_retries)

    return jobs_data


def load_jobs_json_from_file(path: str) -> Dict[str, Any]:
    """Load workflow job data from a local JSON file."""
    validate_json_file_path(path)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        error(f"JSON in file {path} is invalid: {exc}")
    except OSError as exc:
        error(f"Failed to read JSON file {path}: {exc}")

    if not isinstance(data, dict):
        error(f"Top-level JSON structure in {path} is not an object.")

    return data


def validate_json_file_path(path: str) -> None:
    """Ensure a supplied JSON path exists and points to a file."""
    if not os.path.exists(path):
        error(f"JSON file not found: {path}")

    if not os.path.isfile(path):
        error(f"JSON path is not a file: {path}")


def normalise_job_name(raw: str) -> str:
    """Normalise a job name for display and matching."""
    raw = str(raw or "")
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]

    return raw.strip()


def parse_ignored_jobs(raw: str) -> Set[str]:
    """Parse a comma-separated list of ignored job names."""
    ignored: Set[str] = set()

    for part in raw.split(","):
        name = normalise_job_name(part)
        if name:
            ignored.add(name.casefold())

    return ignored


def empty_job_buckets() -> JobBuckets:
    """Create an empty result bucket mapping."""
    return {key: [] for key in JOB_BUCKET_ORDER}


def extract_api_job_record(job: Dict[str, Any]) -> JobRecord:
    """Convert a GitHub API job object into a JobRecord."""
    raw_name = str(job.get("name") or "")
    status = str(job.get("status") or "unknown")
    conclusion = str(job.get("conclusion") or "unknown")
    html_url = str(job.get("html_url") or "")

    if status.lower() != "completed":
        conclusion = f"not_completed:{status}"

    return raw_name, conclusion, status, html_url


def extract_api_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    """Extract job records from a GitHub Actions API jobs response."""
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return None

    return [extract_api_job_record(job) for job in jobs if isinstance(job, dict)]


def extract_needs_job_record(key: str, value: Any) -> JobRecord:
    """Convert a workflow needs entry into a JobRecord."""
    if isinstance(value, dict):
        result = value.get("result") or value.get("conclusion") or "unknown"
        status = value.get("status") or "completed"
    else:
        result = "unknown"
        status = "completed"

    return str(key), str(result), str(status), ""


def extract_needs_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    """Extract job records from a needs-style JSON object."""
    if not isinstance(data, dict):
        return None

    return [extract_needs_job_record(key, value) for key, value in data.items()]


def extract_job_records(data: Dict[str, Any]) -> Iterable[JobRecord]:
    """Extract job records from a supported job-result JSON structure."""
    job_records = extract_api_jobs(data)
    if job_records is None:
        job_records = extract_needs_jobs(data)

    if not job_records:
        error("Unsupported JSON structure for job results.")

    return job_records


def should_ignore_job(job_name: str, ignored_job_names: Optional[Set[str]]) -> bool:
    """Return whether a job should be excluded from the summary."""
    if not ignored_job_names:
        return False

    return job_name.casefold() in ignored_job_names


def add_job_to_bucket(
    buckets: JobBuckets,
    job_name: str,
    raw_result: str,
    html_url: str,
) -> None:
    """Add a job to the correct result bucket."""
    result = normalise_result(raw_result)

    if result.startswith("not_completed:"):
        status = result.split(":", 1)[1] or "unknown"
        buckets["not_completed"].append((f"{job_name} ({status})", html_url))
    elif result in buckets:
        buckets[result].append((job_name, html_url))
    else:
        buckets["other"].append((f"{job_name}: {result}", html_url))


def bucket_jobs(
    data: Dict[str, Any],
    ignored_job_names: Optional[Set[str]] = None,
) -> JobBuckets:
    """Group jobs by their normalised result."""
    buckets = empty_job_buckets()

    for raw_name, raw_result, _raw_status, html_url in extract_job_records(data):
        job_name = normalise_job_name(raw_name)
        if not job_name:
            continue

        if should_ignore_job(job_name, ignored_job_names):
            continue

        add_job_to_bucket(buckets, job_name, raw_result, html_url)

    return buckets


def maybe_read_pr_metadata() -> Tuple[str, str]:
    """Read pull request number and title from GITHUB_EVENT_PATH when present."""
    payload = read_github_event_payload()
    if not payload:
        return "", ""

    pr = payload.get("pull_request") or {}
    if not isinstance(pr, dict):
        return "", ""

    number = pr.get("number")
    title = pr.get("title")

    if number:
        return str(number), str(title or "")

    return "", ""


def read_github_event_payload() -> Optional[Dict[str, Any]]:
    """Read and parse the GitHub Actions event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.isfile(event_path):
        return None

    try:
        with open(event_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def build_run_url(repo: str, run_id: str) -> str:
    """Build a GitHub Actions run URL."""
    if repo and run_id:
        return f"https://github.com/{repo}/actions/runs/{run_id}"

    return ""


def build_commit_url(repo: str, sha: str) -> str:
    """Build a GitHub commit URL."""
    if repo and sha:
        return f"https://github.com/{repo}/commit/{sha}"

    return ""


def build_pr_url(repo: str, pr_number: str) -> str:
    """Build a GitHub pull request URL."""
    if repo and pr_number:
        return f"https://github.com/{repo}/pull/{pr_number}"

    return ""


def print_count_summary(buckets: JobBuckets, out: TextIO) -> None:
    """Write the result count summary table."""
    print(f"### {EMOJI_SUMMARY} Result summary", file=out)
    print(file=out)
    print("| Status | Count |", file=out)
    print("| :----- | ----: |", file=out)

    for key in JOB_BUCKET_ORDER:
        count = len(buckets.get(key, []))
        print(f"| {status_label(key)} | {count} |", file=out)

    print(file=out)


def unique_items(items: List[Tuple[str, str]]) -> Dict[str, str]:
    """Return unique job names while preserving their first URL."""
    unique: Dict[str, str] = {}

    for name, url in items:
        if name and name not in unique:
            unique[name] = url

    return unique


def print_sorted_section(
    items: List[Tuple[str, str]],
    title: str,
    out: TextIO,
) -> None:
    """Write a sorted Markdown bullet list for a result section."""
    if not items:
        return

    unique = unique_items(items)
    if not unique:
        return

    print(f"### {title}", file=out)

    for name in sorted(unique, key=str.casefold):
        print_job_list_item(name, unique[name], out)

    print(file=out)


def print_job_list_item(name: str, url: str, out: TextIO) -> None:
    """Write a single Markdown job list item."""
    if url:
        print(f"- [{md_table_value(name)}]({url})", file=out)
    else:
        print(f"- {md_table_value(name)}", file=out)


def env_value(name: str, default: str = "") -> str:
    """Read a string environment variable."""
    return os.environ.get(name, default)


def first_line(value: str) -> str:
    """Return the first non-newline display line from a string."""
    return value.splitlines()[0].strip() if value else ""


def workflow_metadata() -> Dict[str, str]:
    """Collect workflow metadata from the GitHub Actions environment."""
    pr_number, pr_title = maybe_read_pr_metadata()

    metadata = {
        "repo": env_value("GITHUB_REPOSITORY"),
        "workflow": env_value("GITHUB_WORKFLOW"),
        "workflow_ref": env_value("GITHUB_WORKFLOW_REF"),
        "run_number": env_value("GITHUB_RUN_NUMBER"),
        "run_attempt": env_value("GITHUB_RUN_ATTEMPT"),
        "event_name": env_value("GITHUB_EVENT_NAME"),
        "actor": env_value("GITHUB_ACTOR", "unknown"),
        "triggering_actor": env_value("GITHUB_TRIGGERING_ACTOR"),
        "ref_name": env_value("GITHUB_REF_NAME"),
        "sha": env_value("GITHUB_SHA"),
        "run_id": env_value("GITHUB_RUN_ID"),
        "pr_number": pr_number,
        "pr_title": pr_title,
        "generated_at": build_human_timestamp(),
    }

    metadata["workflow_file"] = workflow_file_name_from_ref(metadata["workflow_ref"])
    metadata["run_url"] = build_run_url(metadata["repo"], metadata["run_id"])
    metadata["commit_url"] = build_commit_url(metadata["repo"], metadata["sha"])
    metadata["pr_url"] = build_pr_url(metadata["repo"], metadata["pr_number"])
    metadata["commit_message"] = build_commit_message(metadata["pr_title"])

    return metadata


def build_commit_message(pr_title: str) -> str:
    """Choose the best commit/message text for workflow metadata."""
    if pr_title:
        return first_line(pr_title)

    return first_line(env_value("GITHUB_COMMIT_MESSAGE"))


def print_metadata_header(out: TextIO) -> None:
    """Write the workflow metadata section header and table header."""
    print(f"### {EMOJI_METADATA} Workflow metadata", file=out)
    print(file=out)
    print("|  |  |", file=out)
    print("| :-- | :-- |", file=out)


def print_metadata_row(label: str, value: str, out: TextIO) -> None:
    """Write a single workflow metadata table row."""
    print(f"| {label} | {md_table_value(value)} |", file=out)


def print_link_metadata_row(label: str, value: str, url: str, out: TextIO) -> None:
    """Write a workflow metadata row that may contain a Markdown link."""
    print(f"| {label} | {make_link(value, url) if url else md_table_value(value)} |", file=out)


def print_metadata_table(out: TextIO) -> None:
    """Write the workflow metadata table."""
    metadata = workflow_metadata()

    print_metadata_header(out)
    print_metadata_row(f"{EMOJI_REPO} Repository", metadata["repo"], out)
    print_metadata_row(f"{EMOJI_WORKFLOW} Workflow", metadata["workflow"], out)

    if metadata["workflow_file"]:
        print_metadata_row(f"{EMOJI_WORKFLOW_FILE} Workflow file", metadata["workflow_file"], out)

    print_link_metadata_row(f"{EMOJI_RUN} Run", f"#{metadata['run_number']}", metadata["run_url"], out)
    print_metadata_row(f"{EMOJI_ATTEMPT} Attempt", metadata["run_attempt"], out)
    print_metadata_row(f"{EMOJI_EVENT} Event", metadata["event_name"], out)
    print_metadata_row(f"{EMOJI_ACTOR} Actor", metadata["actor"], out)

    if metadata["triggering_actor"] and metadata["triggering_actor"] != metadata["actor"]:
        print_metadata_row(f"{EMOJI_TRIGGERING_ACTOR} Triggering actor", metadata["triggering_actor"], out)

    print_metadata_row(f"{EMOJI_BRANCH} Ref", metadata["ref_name"], out)
    print_commit_metadata(metadata, out)
    print_pull_request_metadata(metadata, out)
    print_metadata_row(f"{EMOJI_GENERATED} Generated at (UTC)", metadata["generated_at"], out)
    print(file=out)


def print_commit_metadata(metadata: Dict[str, str], out: TextIO) -> None:
    """Write commit metadata rows when commit details are available."""
    if metadata["sha"]:
        commit_label = f"`{short_sha(metadata['sha'])}`"
        print_link_metadata_row(f"{EMOJI_COMMIT} Commit", commit_label, metadata["commit_url"], out)

    if metadata["commit_message"]:
        print_metadata_row(f"{EMOJI_COMMIT} Commit message", metadata["commit_message"], out)


def print_pull_request_metadata(metadata: Dict[str, str], out: TextIO) -> None:
    """Write pull request metadata rows when pull request details are available."""
    if not metadata["pr_number"]:
        return

    pr_label = (
        f"#{metadata['pr_number']}: {metadata['pr_title']}"
        if metadata["pr_title"]
        else f"#{metadata['pr_number']}"
    )
    print_link_metadata_row(f"{EMOJI_PR} Pull request", pr_label, metadata["pr_url"], out)


def write_markdown_summary(buckets: JobBuckets, out: TextIO) -> None:
    """Write the complete Markdown workflow summary."""
    print(f"# {EMOJI_SUMMARY} Job Status Overview", file=out)
    print(file=out)

    print_count_summary(buckets, out)
    print_job_sections(buckets, out)
    print_metadata_table(out)


def print_job_sections(buckets: JobBuckets, out: TextIO) -> None:
    """Write all non-empty job result sections."""
    for key in JOB_SECTION_ORDER:
        print_sorted_section(buckets[key], section_title(key), out)


def output_paths() -> List[str]:
    """Return all output paths that should receive the Markdown summary."""
    paths: List[str] = []

    summary_path = env_value("GITHUB_STEP_SUMMARY").strip()
    artifact_path = env_value("WORKFLOW_SUMMARY_FILE").strip()

    if summary_path:
        paths.append(summary_path)

    if not artifact_path:
        artifact_path = default_summary_filename()
        os.environ["WORKFLOW_SUMMARY_FILE"] = artifact_path

    if artifact_path and artifact_path not in paths:
        paths.append(artifact_path)

    return paths


def output_mode(path: str) -> str:
    """Return the file mode to use for a summary output path."""
    summary_path = env_value("GITHUB_STEP_SUMMARY").strip()
    return "a" if path == summary_path else "w"


def write_summary_file(path: str, buckets: JobBuckets) -> None:
    """Write the Markdown summary to one file."""
    try:
        with open(path, output_mode(path), encoding="utf-8") as out:
            write_markdown_summary(buckets, cast(TextIO, out))
    except OSError as exc:
        error(f"Failed to write summary file {path}: {exc}")


def write_summaries(buckets: JobBuckets) -> None:
    """Write the Markdown summary to all configured destinations."""
    paths = output_paths()

    if not paths:
        write_markdown_summary(buckets, sys.stdout)
        return

    for path in paths:
        write_summary_file(path, buckets)


def load_jobs_data_from_args(args: List[str]) -> Dict[str, Any]:
    """Load job data from CLI arguments or the GitHub Actions API."""
    if len(args) == 1:
        return load_jobs_json_from_file(args[0])

    if len(args) > 1:
        error("Usage: workflow-summary.py [jobs.json]")

    return fetch_jobs_json_from_api()


def ignored_job_names_from_env() -> Optional[Set[str]]:
    """Read ignored job names from the WORKFLOW_IGNORE_JOBS environment variable."""
    raw_ignored_jobs = env_value("WORKFLOW_IGNORE_JOBS")
    if raw_ignored_jobs.strip():
        return parse_ignored_jobs(raw_ignored_jobs)

    return None


def main() -> None:
    """Run the workflow summary generator."""
    data = load_jobs_data_from_args(sys.argv[1:])
    buckets = bucket_jobs(data, ignored_job_names=ignored_job_names_from_env())
    write_summaries(buckets)


if __name__ == "__main__":
    main()
