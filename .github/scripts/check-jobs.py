#!/usr/bin/env python3
"""
GitHub Actions job status summariser.

This script is designed to be run inside a GitHub Actions job to generate a
human-readable summary of the current workflow run's job statuses and append
that summary to the step summary file exposed via the `GITHUB_STEP_SUMMARY`
environment variable.

It supports two modes of operation:

1. API mode (default)
   - No CLI arguments are provided.
   - The script reads the following environment variables:
       - GITHUB_REPOSITORY  (e.g. "owner/repo")
       - GITHUB_RUN_ID      (numeric ID of the current workflow run)
       - GITHUB_TOKEN or ACTIONS_RUNTIME_TOKEN
   - It calls the GitHub REST API:
       GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100
   - It expects a response in the standard GitHub jobs shape:
       {
         "jobs": [
           { "name": "...", "conclusion": "success", ... },
           ...
         ]
       }

2. File mode
   - A single CLI argument is provided:
       python check-jobs.py path/to/jobs.json
   - The file is expected to contain JSON in one of the supported shapes:
       a) GitHub /jobs API shape (see above)
       b) toJson(needs) style mapping:
          { "job_id": { "result": "success", ... }, ... }

The script normalises job results into buckets:
    - success
    - failure
    - cancelled
    - skipped
    - timed_out
    - other (for unknown/unsupported result values: stored as "name:result")

An optional ignore list can be provided via the CHECK_JOBS_IGNORE_JOBS
environment variable:

    CHECK_JOBS_IGNORE_JOBS
        Comma-separated list of job names to ignore in the summary. Job
        names are normalised using the same logic as normalise_job_name
        (segment after the last "/" and trimmed) and compared
        case-insensitively.

On success, a Markdown summary is appended to the file pointed to by
GITHUB_STEP_SUMMARY. On any error (configuration, network, JSON, or structure),
an error message is written to stderr and the script exits with status 1.

This script is intentionally dependency-free (only uses the Python standard
library) so it can run on GitHub-hosted runners without additional setup.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Set, TextIO, Tuple
from urllib.error import HTTPError, URLError


JobRecord = Tuple[str, str]  # (raw_name, raw_result)

# ---------------------------------------------------------------------------#
# Utility helpers
# ---------------------------------------------------------------------------#

def error(message: str, *, code: int = 1) -> NoReturn:
    """
    Print an error message to stderr and exit with the given status code.

    Args:
        message: Human-readable error message to write to stderr.
        code: Exit status code to use when terminating the process.

    Raises:
        SystemExit: Always raised to terminate the script.
    """
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def ordinal_suffix(day: int) -> str:
    """
    Return the HTML `<sup>` ordinal suffix for a given day of the month.

    Args:
        day: Day of the month as an integer (1–31).

    Returns:
        A string containing the ordinal suffix wrapped in `<sup>`, e.g.
        "<sup>st</sup>", "<sup>nd</sup>", "<sup>rd</sup>", or "<sup>th</sup>".
    """
    if day in (1, 21, 31):
        suf = "st"
    elif day in (2, 22):
        suf = "nd"
    elif day in (3, 23):
        suf = "rd"
    else:
        suf = "th"
    return f"<sup>{suf}</sup>"


def build_human_timestamp() -> str:
    """
    Build a human-readable UTC timestamp similar to the original Bash script.

    The format is:
        "Monday 24<sup>th</sup> November 2025 18:03:45"

    Returns:
        A formatted string representing the current UTC time with an ordinal
        suffix on the day number.
    """
    now = datetime.now(timezone.utc)
    day = now.day
    suffix = ordinal_suffix(day)
    dow = now.strftime("%A")
    month_name = now.strftime("%B")
    year = now.strftime("%Y")
    time_str = now.strftime("%H:%M:%S")
    return f"{dow} {day}{suffix} {month_name} {year} {time_str}"

# ---------------------------------------------------------------------------#
# Input loading (API / file)
# ---------------------------------------------------------------------------#

def _get_github_context_from_env() -> Tuple[str, str, str]:
    """
    Read and validate the core GitHub context from environment variables.

    Returns:
        A 3-tuple of (repo, run_id, token).

    Raises:
        SystemExit:
            If any required value is missing.
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACTIONS_RUNTIME_TOKEN")

    if not repo or not run_id:
        error("GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API.", code=1)

    if not token:
        error("GITHUB_TOKEN (or ACTIONS_RUNTIME_TOKEN) is not set; cannot call GitHub API.", code=1)

    return repo, run_id, token


def _fetch_jobs_json(repo: str, run_id: str, token: str) -> Dict[str, Any]:
    """
    Fetch job metadata for a given workflow run.

    This is a required call: failures are treated as fatal.

    Args:
        repo: Repository slug, e.g. "owner/repo".
        run_id: Workflow run ID.
        token: GitHub token for authentication.

    Returns:
        Parsed JSON dictionary from the jobs API.

    Raises:
        SystemExit:
            On network/HTTP/JSON errors or unexpected response structure.
    """
    jobs_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-check-jobs-status",
    }

    req = urllib.request.Request(jobs_url, headers=headers)

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
        error(f"GitHub API returned HTTP {exc.code} when fetching jobs: {exc.reason}", code=1)
    except URLError as exc:
        error(f"Failed to reach GitHub API when fetching jobs: {exc.reason}", code=1)
    except Exception as exc:  # pragma: no cover - defensive catch-all
        error(f"Unexpected error when calling GitHub jobs API: {exc}", code=1)

    if status != 200:
        body = body_bytes.decode("utf-8", errors="replace")
        print("GitHub API response body (jobs):", file=sys.stderr)
        print(body, file=sys.stderr)
        error(f"GitHub API returned HTTP {status} when fetching jobs.", code=1)

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode GitHub jobs API JSON: {exc}", code=1)

    if not isinstance(data, dict):
        error(
            "GitHub jobs API returned JSON, but the top-level structure is not an object as expected.",
            code=1,
        )

    return data


def _maybe_set_commit_message_env(repo: str, run_id: str, token: str) -> None:
    """
    Best-effort fetch of the workflow run to capture the head commit message.

    On success, stores the commit message in the GITHUB_COMMIT_MESSAGE
    environment variable for later use in the summary.

    Any errors here are non-fatal and silently ignored.

    Args:
        repo: Repository slug, e.g. "owner/repo".
        run_id: Workflow run ID.
        token: GitHub token for authentication.
    """
    run_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-check-jobs-status",
    }

    req = urllib.request.Request(run_url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body_bytes = resp.read()
    except Exception:
        return

    if status != 200 or not body_bytes:
        return

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError:
        return

    if not isinstance(data, dict):
        return

    head_commit = data.get("head_commit") or {}
    message = str(head_commit.get("message") or "").strip()
    if message:
        os.environ["GITHUB_COMMIT_MESSAGE"] = message


def fetch_jobs_json_from_api() -> Dict[str, Any]:
    """
    Fetch job metadata for the current workflow run via the GitHub REST API.

    This function:

      1. Reads and validates the GitHub context from environment variables.
      2. Fetches the jobs JSON (fatal on failure).
      3. Best-effort fetches the workflow run to capture the head commit
         message for use in the step summary.

    Returns:
        A dictionary representing the JSON response from the GitHub jobs API.
    """
    repo, run_id, token = _get_github_context_from_env()

    jobs_data = _fetch_jobs_json(repo, run_id, token)
    _maybe_set_commit_message_env(repo, run_id, token)

    return jobs_data


def load_jobs_json_from_file(path: str) -> Dict[str, Any]:
    """
    Load jobs JSON from a file path for offline/testing usage.

    The file is expected to contain JSON in one of the supported shapes:
        - GitHub /jobs API shape
        - toJson(needs) style mapping

    Args:
        path: Filesystem path to a JSON file.

    Returns:
        A dictionary parsed from the given JSON file.

    Raises:
        SystemExit: If the file does not exist, cannot be read, or contains
            invalid JSON, or if the top-level structure is not a dictionary.
    """
    if not os.path.exists(path):
        error(f"JSON file not found: {path}", code=1)

    if not os.path.isfile(path):
        error(f"JSON path is not a file: {path}", code=1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        error(f"JSON in file {path} is invalid: {exc}", code=1)
    except OSError as exc:
        error(f"Failed to read JSON file {path}: {exc}", code=1)

    if not isinstance(data, dict):
        error(f"Top-level JSON structure in {path} is not an object; a dictionary is required.", code=1)

    return data


def parse_ignored_jobs(raw: str) -> Set[str]:
    """
    Parse a comma-separated list of job names to ignore.

    Names are normalised via :func:`normalise_job_name` and lowercased
    so comparisons are case-insensitive and consistent with the way job
    names are displayed in the summary.

    Args:
        raw:
            Comma-separated string from ``CHECK_JOBS_IGNORE_JOBS``.

    Returns:
        A set of normalised, lowercased job names to ignore.
    """
    ignored: Set[str] = set()

    for part in raw.split(","):
        name = normalise_job_name(part)
        if not name:
            continue
        ignored.add(name.casefold())

    return ignored

# ---------------------------------------------------------------------------#
# Normalisation and bucketing
# ---------------------------------------------------------------------------#


def normalise_job_name(raw: str) -> str:
    """
    Normalise a raw job name into a canonical form.

    Behaviour:
      - If the name contains a slash ("/"), only the right-hand side is kept.
      - Leading and trailing whitespace is stripped.

    Args:
        raw: Raw job name from the API or JSON structure.

    Returns:
        A normalised job name string. May be an empty string if the input
        contained only whitespace.
    """
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    return raw.strip()


def _extract_api_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    """
    Extract (name, conclusion) pairs from the GitHub /jobs API shape.

    The expected shape is:
        {
          "jobs": [
            { "name": "...", "conclusion": "success", "status": "completed", ... },
            ...
          ]
        }

    Only jobs with ``status == "completed"`` are included. Jobs that are
    still in progress, queued, or otherwise not completed are ignored to
    avoid showing them as "unknown" in the summary.

    Args:
        data: Parsed JSON dictionary from the GitHub jobs API.

    Returns:
        An iterable of (raw_name, raw_result) tuples if the structure matches,
        otherwise None.
    """
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return None

    records: List[JobRecord] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue

        status = str(job.get("status") or "").lower()
        if status != "completed":
            # Skip jobs that have not completed yet; they don't have a stable
            # conclusion and would otherwise be shown as "unknown".
            continue

        raw_name = str(job.get("name", ""))
        conclusion = str(job.get("conclusion", "unknown") or "unknown")
        records.append((raw_name, conclusion))

    return records


def _extract_needs_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    """
    Extract (name, result) pairs from a toJson(needs)-style mapping.

    The expected shape is:
        {
          "job_id": { "result": "success", ... },
          ...
        }

    For defensive compatibility, this function will also look for
    a "conclusion" field if "result" is not present.

    Args:
        data: Parsed JSON dictionary representing the toJson(needs) mapping.

    Returns:
        An iterable of (raw_name, raw_result) tuples if the structure matches,
        otherwise None.
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


def bucket_jobs(
    data: Dict[str, Any],
    ignored_job_names: Optional[Set[str]] = None,
) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
    """
    Bucket jobs into status lists from a JSON object.

    The function supports both:
        1) GitHub /jobs API format:
           { "jobs": [ { "name": "...", "conclusion": "success" }, ... ] }

        2) toJson(needs) style:
           { "job_id": { "result": "success", ... }, ... }

    Jobs are normalised and then distributed into the following buckets:
        - success
        - failure
        - cancelled
        - skipped
        - timed_out
        - other (for any unknown/unsupported result, as "name:result")

    Args:
        data: Parsed JSON dictionary representing either a GitHub /jobs response
            or a toJson(needs) mapping.
        ignored_job_names:
            Optional set of normalised job names to exclude from the summary.
            Comparisons are done case-insensitively.

    Returns:
        A 6-tuple of lists:
            (success, failure, cancelled, skipped, timed_out, other)

    Raises:
        SystemExit: If the JSON structure does not match any supported shape.
    """
    success: List[str] = []
    failure: List[str] = []
    cancelled: List[str] = []
    skipped: List[str] = []
    timed_out: List[str] = []
    other: List[str] = []

    # 1) Normalise into a list of (raw_name, raw_result) pairs
    job_records: Optional[Iterable[JobRecord]] = None

    if isinstance(data, dict):
        job_records = _extract_api_jobs(data)
        if job_records is None:
            job_records = _extract_needs_jobs(data)

    if not job_records:
        error("Unsupported JSON structure for job results.", code=1)

    # Assert for type-checkers: after the error() call above, job_records is not None
    assert job_records is not None

    # 2) Single pass to normalise + bucket
    buckets: Dict[str, List[str]] = {
        "success": success,
        "failure": failure,
        "cancelled": cancelled,
        "skipped": skipped,
        "timed_out": timed_out,
    }

    ignored_normalised: Set[str] = set()
    if ignored_job_names:
        # Normalise to casefold() for robust comparisons
        ignored_normalised = {name.casefold() for name in ignored_job_names}

    for raw_name, raw_result in job_records:
        job_name = normalise_job_name(raw_name)
        if not job_name:
            continue

        # Skip any job whose normalised name is in the ignore list.
        if ignored_normalised and job_name.casefold() in ignored_normalised:
            continue

        result = raw_result or "unknown"
        bucket = buckets.get(result)
        if bucket is not None:
            bucket.append(job_name)
        else:
            other.append(f"{job_name}:{result}")

    return success, failure, cancelled, skipped, timed_out, other

# ---------------------------------------------------------------------------#
# Output formatting
# ---------------------------------------------------------------------------#


def print_sorted_section(lines: List[str], title: str, out: TextIO) -> None:
    """
    Print a Markdown section for a given job bucket.

    The output format is:
        ### {title}
        - Job A
        - Job B

    Jobs are deduplicated and sorted alphabetically (case-insensitive).

    Args:
        lines: List of job names for this bucket.
        title: Section heading to use in the Markdown summary.
        out: A writable text stream, typically the step summary file.
    """
    if not lines:
        return
    print(f"### {title}", file=out)
    for name in sorted(set(lines), key=str.casefold):
        if not name:
            continue
        print(f"- {name}", file=out)
    print(file=out)


def maybe_read_pr_metadata() -> Tuple[str, str]:
    """
    Attempt to read pull request metadata from GITHUB_EVENT_PATH.

    If the current workflow run is associated with a pull request event and
    the event payload contains a `pull_request` object, this function extracts
    the PR number and title.

    Environment variables used:
        - GITHUB_EVENT_PATH

    Returns:
        A tuple of (pr_number, pr_title). If no PR information is available
        or parsing fails, both elements will be empty strings.
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


def write_step_summary(success: List[str], failure: List[str], cancelled: List[str], skipped: List[str], timed_out: List[str], other: List[str]) -> None:
    """
    Append a Markdown job status summary to the GitHub step summary file.

    Environment variables used:
        - GITHUB_STEP_SUMMARY       (path to the summary file)
        - GITHUB_REPOSITORY
        - GITHUB_WORKFLOW
        - GITHUB_RUN_NUMBER
        - GITHUB_RUN_ATTEMPT
        - GITHUB_EVENT_NAME
        - GITHUB_ACTOR
        - GITHUB_TRIGGERING_ACTOR
        - GITHUB_REF_NAME
        - GITHUB_SHA
        - GITHUB_RUN_ID
        - GITHUB_EVENT_PATH         (for PR metadata)

    Args:
        success: List of job names that completed successfully.
        failure: List of job names that failed.
        cancelled: List of job names that were cancelled.
        skipped: List of job names that were skipped.
        timed_out: List of job names that timed out.
        other: List of "name:result" strings for jobs with non-standard results.

    Raises:
        SystemExit: If the step summary path is set but cannot be written to.
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        # Not running in GitHub Actions (or summaries disabled)
        return

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    workflow = os.environ.get("GITHUB_WORKFLOW", "")
    run_number = os.environ.get("GITHUB_RUN_NUMBER", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    actor = os.environ.get("GITHUB_ACTOR", "unknown")
    triggering_actor = os.environ.get("GITHUB_TRIGGERING_ACTOR", "")
    ref_name = os.environ.get("GITHUB_REF_NAME", "")
    sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")

    pr_number, pr_title = maybe_read_pr_metadata()
    generated_at = build_human_timestamp()

    try:
        with open(summary_path, "a", encoding="utf-8") as out:
            print("## Job Status Overview", file=out)
            print(file=out)

            print_sorted_section(success, "Successful jobs", out)
            print_sorted_section(failure, "Failed jobs", out)
            print_sorted_section(timed_out, "Timed out jobs", out)
            print_sorted_section(cancelled, "Cancelled jobs", out)
            print_sorted_section(skipped, "Skipped jobs", out)
            print_sorted_section(other, "Other statuses", out)

            print("### Workflow metadata", file=out)
            print(file=out)
            print("| Field  | Value   |", file=out)
            print("| :----- | :------ |", file=out)

            print(f"| Repository | {repo} |", file=out)
            print(f"| Workflow | {workflow} |", file=out)
            print(f"| Run number | #{run_number} |", file=out)
            print(f"| Attempt | {run_attempt} |", file=out)
            print(f"| Event | {event_name} |", file=out)

            print(f"| Actor | {actor} |", file=out)
            if triggering_actor and triggering_actor != actor:
                print(f"| Triggering actor | {triggering_actor} |", file=out)

            print(f"| Ref | {ref_name} |", file=out)
            print(f"| Commit SHA | {sha} |", file=out)
            # Try commit message from PR event first
            commit_message = ""
            if pr_title:
                commit_message = pr_title
            else:
                # Fallback to commit message if available
                commit = os.environ.get("GITHUB_COMMIT_MESSAGE", "")
                if commit:
                    commit_message = commit

            if commit_message:
                print(f"| Commit Message | {commit_message} |", file=out)
            if repo and run_id:
                print(f"| Run URL | https://github.com/{repo}/actions/runs/{run_id} |", file=out)

            if pr_number:
                print(f"| PR | #{pr_number}: {pr_title} |", file=out)
                if repo:
                    print(f"| PR URL | https://github.com/{repo}/pull/{pr_number} |", file=out)

            print(f"| Generated at (UTC) | {generated_at} |", file=out)
            print(file=out)
    except OSError as exc:
        error(f"Failed to open GITHUB_STEP_SUMMARY file for writing: {exc}", code=1)

# ---------------------------------------------------------------------------#
# Entry point
# ---------------------------------------------------------------------------#


def main() -> None:
    """
    Entry point for the job status summariser.

    Behaviour:
        - If a single CLI argument is provided, it is treated as a path to a
          JSON file containing job results.
        - Otherwise, the script operates in API mode and queries the GitHub
          jobs endpoint for the current run.

    On success, a Markdown summary is appended to the GitHub step summary file
    (if available). On failure, an error is printed to stderr and the process
    exits with status 1.
    """
    # Decide where to get job JSON from
    if len(sys.argv) == 2:
        data = load_jobs_json_from_file(sys.argv[1])
    else:
        data = fetch_jobs_json_from_api()

    # Optional: list of jobs to ignore in the summary.
    raw_ignored_jobs = os.environ.get("CHECK_JOBS_IGNORE_JOBS", "")
    ignored_job_names: Optional[Set[str]] = None
    if raw_ignored_jobs.strip():
        ignored_job_names = parse_ignored_jobs(raw_ignored_jobs)

    success, failure, cancelled, skipped, timed_out, other = bucket_jobs(
        data,
        ignored_job_names=ignored_job_names,
    )
    write_step_summary(success, failure, cancelled, skipped, timed_out, other)


if __name__ == "__main__":
    main()
