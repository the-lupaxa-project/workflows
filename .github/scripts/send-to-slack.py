#!/usr/bin/env python3
"""
Slack workflow status notifier for GitHub Actions.

This script is a Python reimplementation of the core behaviour of
Gamesight/slack-workflow-status, adapted to run as a standalone script
inside a GitHub Actions job.

Overview
========
The script:

  - Queries the GitHub REST API to fetch metadata for the **current workflow
    run** and its associated **jobs**.
  - Filters jobs to those with ``status == "completed"``.
  - Determines a **workflow colour** and **headline message** based on job
    conclusions, mirroring the original action:

        - colour: ``"good"`` / ``"warning"`` / ``"danger"``
        - message: ``"Success:"`` / ``"Cancelled:"`` / ``"Failed:"``

  - Builds per-job Slack “fields” such as:

        ``"✓ <job_link|Job name> (1m 23s)"``

  - Assembles a Slack attachment with:

        - A status line (actor, event type, branch or PR)
        - A workflow details line (workflow name, run number, duration)
        - An optional commit message line
        - A footer linking back to the repository
        - One field per completed job (unless disabled by configuration)

  - Sends the resulting payload to a Slack Incoming Webhook.

The Slack message layout is designed to be visually compatible with
`Gamesight/slack-workflow-status` so that you can swap the implementations
without significant visual changes.

Environment Configuration
=========================

Required environment variables
------------------------------
- ``SLACK_WEBHOOK_URL``
    Incoming Slack Webhook URL. This is where the JSON payload will be sent.

- ``GITHUB_REPOSITORY``
    Repository slug for the current workflow run, e.g. ``"owner/repo"``.

- ``GITHUB_RUN_ID``
    Numeric ID of the current workflow run.

- ``GITHUB_TOKEN`` or ``ACTIONS_RUNTIME_TOKEN``
    Token with permission to call the GitHub Actions API for the repository.

Optional behaviour controls
---------------------------
- ``SEND_TO_SLACK_RESULTS``
    Comma-separated list of workflow conclusions that should trigger a Slack
    notification (e.g. ``"failure,cancelled,timed_out"``).
    Use ``"all"`` (default) to notify regardless of conclusion.

- ``SEND_TO_SLACK_INCLUDE_JOBS``
    Controls whether per-job fields are included:

        - ``"true"``       – always include job fields (default)
        - ``"false"``      – never include job fields
        - ``"on-failure"`` – include job fields only when the overall workflow
                             conclusion is **not** ``"success"``

- ``SEND_TO_SLACK_INCLUDE_COMMIT_MESSAGE``
    ``"true"`` (default) to append a line
    ``"Commit: <workflow_run.head_commit.message>"`` if available.

- ``SEND_TO_SLACK_JOBS_TO_FETCH``
    Integer used as ``per_page`` when requesting jobs from the GitHub API.
    Defaults to ``"30"``. Values <= 0 are treated as the default.

- ``SEND_TO_SLACK_IGNORE_JOBS``
    Comma-separated list of job names to exclude from the per-job Slack
    fields. Job names are normalised using the same logic as
    :func:`normalise_job_name` (e.g. stripping prefixes before the last
    ``"/"`` and trimming whitespace), and matched case-insensitively.

Optional cosmetic configuration
-------------------------------
These mirror the Gamesight action inputs and are applied directly to the
Slack payload:

- ``SEND_TO_SLACK_CHANNEL`` / ``SLACK_CHANNEL``
    Override the Slack channel (e.g. ``"#ci-status"``).

- ``SEND_TO_SLACK_NAME`` / ``SLACK_NAME``
    Override the bot display name.

- ``SEND_TO_SLACK_ICON_URL`` / ``SLACK_ICON_URL``
    Icon image URL.

- ``SEND_TO_SLACK_ICON_EMOJI`` / ``SLACK_ICON_EMOJI``
    Emoji icon (e.g. ``":wolf:"``).

Exit behaviour
--------------
On any unrecoverable error (missing configuration, GitHub API failure,
JSON decoding error, Slack webhook failure) this script prints a message
to stderr and exits with a non-zero status code.

Implementation notes
--------------------
- Uses **only** the Python standard library.
- Designed to run directly in a GitHub Actions job without extra dependencies.
- Uses helper functions to keep complexity low and behaviour testable.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, NoReturn, Optional, Tuple, Set
from urllib.error import HTTPError, URLError


# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #


def error(message: str, *, code: int = 1) -> NoReturn:
    """
    Print an error message to stderr and terminate the process.

    This helper centralises error handling so that all fatal failures use a
    consistent format and exit behaviour.

    Args:
        message:
            Human-readable error description. The string is prefixed with
            ``"ERROR: "`` when printed.
        code:
            Process exit status code. Defaults to 1.

    Raises:
        SystemExit: Always raised to terminate the script with the given code.
    """
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """
    Parse an ISO 8601 timestamp into a naive UTC ``datetime`` object.

    The GitHub API typically returns timestamps of the form
    ``"YYYY-MM-DDTHH:MM:SSZ"`` or with an explicit offset. This function
    converts them into naive UTC datetimes for simpler duration calculations.

    Args:
        value:
            ISO 8601 timestamp string, or ``None``/empty. A trailing ``"Z"``
            (UTC) is replaced with ``"+00:00"`` to work with
            :func:`datetime.fromisoformat`.

    Returns:
        A naive UTC :class:`datetime` instance if parsing succeeds, or
        ``None`` if the value is empty or cannot be parsed.
    """
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
        # Malformed timestamp; treat as missing.
        return None

    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)

    return dt


def compute_duration(start: datetime, end: datetime) -> str:
    """
    Compute a human-readable duration string between two datetimes.

    The result mirrors the TypeScript implementation in the original
    Gamesight action, using a compact format like:

        - ``"1d 2h 3m 4s"``
        - ``"3m 10s"``
        - ``"20s"``

    If the end time precedes the start time, the duration is treated as zero.

    Args:
        start:
            Start time (naive UTC :class:`datetime`).
        end:
            End time (naive UTC :class:`datetime`).

    Returns:
        A non-empty string describing the elapsed time in days, hours, minutes
        and seconds. If the computed duration is zero, returns ``"0s"``.
    """
    duration_seconds = (end - start).total_seconds()
    if duration_seconds < 0:
        duration_seconds = 0
    delta = int(duration_seconds)

    days = delta // 86400
    delta -= days * 86400
    hours = (delta // 3600) % 24
    delta -= hours * 3600
    minutes = (delta // 60) % 60
    delta -= minutes * 60
    seconds = delta % 60

    def format_duration(value: int, text: str, hide_on_zero: bool) -> str:
        """
        Format a single duration component.

        Args:
            value:
                Numeric time value (e.g. seconds).
            text:
                Unit suffix (e.g. ``"s"`` for seconds).
            hide_on_zero:
                If ``True``, the component is omitted when ``value`` is zero.

        Returns:
            A formatted fragment such as ``"10s "`` or an empty string.
        """
        if value <= 0 and hide_on_zero:
            return ""
        return f"{value}{text} "

    result = (
        format_duration(days, "d", True)
        + format_duration(hours, "h", True)
        + format_duration(minutes, "m", True)
        + format_duration(seconds, "s", False)
    ).strip()

    return result or "0s"


def fetch_json(url: str, token: str, user_agent: str) -> Dict[str, Any]:
    """
    Fetch and decode a JSON object from the GitHub API.

    This function wraps :mod:`urllib.request` with robust error handling, and
    enforces that the decoded JSON payload is a dictionary.

    Args:
        url:
            Fully-qualified GitHub API URL.
        token:
            Bearer token used for GitHub authentication.
        user_agent:
            Value for the ``User-Agent`` header, used for identification.

    Returns:
        A dictionary representing the JSON response body.

    Raises:
        SystemExit:
            If the network request fails, the HTTP status is not 200, the body
            is not valid JSON, or the decoded top-level structure is not a
            dictionary.
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
        error(f"Failed to reach GitHub API at {url}: {exc.reason}", code=1)
    except Exception as exc:  # pragma: no cover - defensive
        error(f"Unexpected error when calling GitHub API at {url}: {exc}", code=1)

    if status != 200:
        body = body_bytes.decode("utf-8", errors="replace")
        if body:
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


def normalise_job_name(raw: str) -> str:
    """
    Normalise a raw GitHub job name into a shorter, canonical form.

    This mirrors the logic used in ``check-jobs.py``:

      - If the string contains a slash (``"/"``), only the segment to the right
        of the last slash is kept. This removes noisy prefixes such as
        matrix labels or reusable workflow names.
      - Leading and trailing whitespace is stripped.

    Args:
        raw:
            Raw job name from the GitHub API.

    Returns:
        A trimmed, normalised job name. May be an empty string if the input
        consists solely of whitespace.
    """
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    return raw.strip()


def parse_ignored_jobs(raw: str) -> Set[str]:
    """
    Parse a comma-separated list of job names to ignore.

    Names are normalised via :func:`normalise_job_name` and lowercased
    so comparisons are case-insensitive and consistent with the way job
    names are displayed.

    Args:
        raw:
            Comma-separated string from ``SEND_TO_SLACK_IGNORE_JOBS``.

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


# --------------------------------------------------------------------------- #
# GitHub data loading (run + jobs)
# --------------------------------------------------------------------------- #


def fetch_run_and_jobs(
    repo: str,
    run_id: str,
    token: str,
    jobs_to_fetch: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Fetch workflow run metadata and associated jobs from the GitHub API.

    This function calls:

      - ``GET /repos/{repo}/actions/runs/{run_id}``
      - ``GET /repos/{repo}/actions/runs/{run_id}/jobs?per_page=...``

    It then filters the jobs list to only those entries with
    ``status == "completed"``.

    Args:
        repo:
            Repository slug (e.g. ``"owner/repo"``).
        run_id:
            ID of the workflow run whose jobs should be inspected.
        token:
            Authentication token used by :func:`fetch_json`.
        jobs_to_fetch:
            Value for the ``per_page`` query parameter when listing jobs.
            Values <= 0 are treated as 30.

    Returns:
        A 2-tuple ``(workflow_run, completed_jobs)``, where:

          - ``workflow_run`` is the run metadata dictionary.
          - ``completed_jobs`` is a list of job dictionaries with
            ``status == "completed"``.

    Raises:
        SystemExit:
            If any of the underlying GitHub API calls fail.
    """
    if jobs_to_fetch <= 0:
        jobs_to_fetch = 30

    base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"

    run = fetch_json(base, token, "lupaxa-send-to-slack")
    jobs_data = fetch_json(
        f"{base}/jobs?per_page={jobs_to_fetch}",
        token,
        "lupaxa-send-to-slack",
    )

    jobs_raw = jobs_data.get("jobs", [])
    if not isinstance(jobs_raw, list):
        jobs_raw = []

    completed_jobs = [
        job for job in jobs_raw if isinstance(job, dict) and job.get("status") == "completed"
    ]

    if not completed_jobs:
        print(
            "Warning: No completed jobs found for this workflow run. "
            "Slack notification will contain no job fields.",
            file=sys.stderr,
        )

    return run, completed_jobs


def get_workflow_conclusion(workflow_run: Dict[str, Any]) -> str:
    """
    Determine the overall conclusion for the workflow run.

    The GitHub API exposes both ``status`` and ``conclusion``. For completed
    runs, ``conclusion`` is preferred. When it is missing, this function
    falls back to ``status`` and normalises the result to lowercase.

    Args:
        workflow_run:
            Dictionary returned by the GitHub API in response to
            ``GET /repos/{repo}/actions/runs/{run_id}``.

    Returns:
        A lowercase workflow conclusion string such as ``"success"``,
        ``"failure"``, ``"cancelled"`` or ``"unknown"`` when neither field
        is available.
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
    Determine the Slack colour and lead message for the workflow.

    The decision mirrors the logic in Gamesight/slack-workflow-status:

      - If **all** completed jobs have a conclusion in ``{"success", "skipped"}``,
        use colour ``"good"`` and lead message ``"Success:"``.
      - Else if **any** completed job has a conclusion of ``"cancelled"``,
        use colour ``"warning"`` and lead message ``"Cancelled:"``.
      - Otherwise, treat the workflow as failed: colour ``"danger"``,
        lead message ``"Failed:"``.

    If there are no completed jobs at all, the function returns
    ``("warning", "Unknown:")``.

    Args:
        completed_jobs:
            List of job dictionaries (typically filtered to status
            ``"completed"``).

    Returns:
        A 2-tuple ``(workflow_color, workflow_msg)`` suitable for use in
        Slack attachments, e.g. ``("good", "Success:")``.
    """
    if not completed_jobs:
        return "warning", "Unknown:"

    conclusions = [str(job.get("conclusion") or "").lower() for job in completed_jobs]

    if all(c in ("success", "skipped") for c in conclusions):
        return "good", "Success:"

    if any(c == "cancelled" for c in conclusions):
        return "warning", "Cancelled:"

    return "danger", "Failed:"


def _should_include_jobs(include_jobs_mode: str, workflow_conclusion: str) -> bool:
    """
    Decide whether job fields should be included in the Slack payload.

    This helper interprets the value of ``SEND_TO_SLACK_INCLUDE_JOBS`` and
    the workflow conclusion:

      - ``"false"``      → never include job fields.
      - ``"on-failure"`` → include job fields only when
                            ``workflow_conclusion != "success"``.
      - any other value  → always include job fields (treated as ``"true"``).

    Args:
        include_jobs_mode:
            Raw include mode from configuration (e.g. ``"true"``,
            ``"false"``, or ``"on-failure"``).
        workflow_conclusion:
            Normalised workflow conclusion, typically obtained from
            :func:`get_workflow_conclusion`.

    Returns:
        ``True`` if job fields should be included in the Slack payload,
        otherwise ``False``.
    """
    mode = (include_jobs_mode or "true").strip().lower()

    if mode == "false":
        return False

    if mode == "on-failure" and workflow_conclusion == "success":
        return False

    return True


def _job_status_icon(conclusion: str) -> str:
    """
    Map a job conclusion string to a single-character status icon.

    This mirrors the original TypeScript logic:

      - ``"success"``               → ``"✓"``
      - ``"cancelled"`` or
        ``"skipped"``               → ``"⃠"``
      - anything else (incl. failure) → ``"✗"``

    Args:
        conclusion:
            Job conclusion string (case-insensitive).

    Returns:
        A single-character string suitable for inclusion in Slack messages.
    """
    conclusion = (conclusion or "").lower()

    if conclusion == "success":
        return "✓"
    if conclusion in ("cancelled", "skipped"):
        return "⃠"
    return "✗"


def _build_single_job_field(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Build a single Slack field object representing a completed job.

    The field is formatted as:

        ``"✓ <job_url|Job name> (1m 23s)"``

    where the icon reflects the job conclusion, and the duration is computed
    from the job's ``started_at`` and ``completed_at`` timestamps if both
    are available.

    Args:
        job:
            Dictionary describing a GitHub Actions job, typically from
            ``/actions/runs/{run_id}/jobs``.

    Returns:
        A dictionary suitable for inclusion in a Slack attachment ``fields``
        array, or ``None`` if required data (name or HTML URL) is missing.
    """
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
    """
    Build the Slack ``fields`` array for completed jobs.

    This function:

      - Applies :func:`_should_include_jobs` to decide if job fields are
        needed at all.
      - Builds a field for each completed job via
        :func:`_build_single_job_field`.
      - Sorts fields by **normalised job name**, case-insensitively, using
        the same ordering semantics as ``check-jobs.py``.

    Args:
        completed_jobs:
            List of completed job dictionaries.
        include_jobs_mode:
            Raw include mode from the environment, e.g. ``"true"``,
            ``"false"`` or ``"on-failure"``.
        workflow_conclusion:
            Normalised workflow conclusion string.
        ignored_job_names:
            Optional set of normalised job names to exclude from the job
            fields. Comparisons are case-insensitive.

    Returns:
        A list of Slack field dictionaries. The list may be empty if job
        fields are disabled or no valid jobs are present.
    """
    if not _should_include_jobs(include_jobs_mode, workflow_conclusion):
        return []

    name_field_pairs: List[Tuple[str, Dict[str, Any]]] = []
    ignored_normalised: Set[str] = set()

    if ignored_job_names:
        # Ensure we compare using casefold() to be robust.
        ignored_normalised = {name.casefold() for name in ignored_job_names}

    for job in completed_jobs:
        field = _build_single_job_field(job)
        if field is None:
            continue

        raw_name = str(job.get("name") or "")
        name = normalise_job_name(raw_name)
        if not name:
            continue

        # Skip any job whose normalised name is in the ignore list.
        if ignored_normalised and name.casefold() in ignored_normalised:
            continue

        name_field_pairs.append((name, field))

    name_field_pairs.sort(key=lambda pair: pair[0].casefold())

    return [field for _name, field in name_field_pairs]


def _get_pull_requests(workflow_run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract the ``pull_requests`` list from a workflow run payload.

    Args:
        workflow_run:
            Workflow run dictionary from the GitHub API.

    Returns:
        A list of pull request dictionaries. Any non-dictionary elements
        are discarded.
    """
    pull_requests = workflow_run.get("pull_requests") or []
    if not isinstance(pull_requests, list):
        return []
    return [pr for pr in pull_requests if isinstance(pr, dict)]


def _is_internal_pull_request(pr: Dict[str, Any], repo_url: str) -> bool:
    """
    Determine whether a pull request targets the same repository.

    External pull requests (originating from forks) are filtered out by
    checking whether the base repository URL matches the workflow run's
    repository URL.

    Args:
        pr:
            Pull request dictionary from the workflow run payload.
        repo_url:
            The canonical API URL of the repository (e.g. from
            ``workflow_run["repository"]["url"]``).

    Returns:
        ``True`` if the PR targets the same repository, otherwise ``False``.
    """
    base = pr.get("base") or {}
    base_repo = base.get("repo") or {}
    base_repo_url = str(base_repo.get("url") or "")
    return bool(repo_url) and base_repo_url == repo_url


def _format_pull_request_segment(pr: Dict[str, Any], html_url: str) -> Optional[str]:
    """
    Format a single pull request segment for inclusion in the status line.

    The format mirrors Gamesight's implementation:

        ``"<repo_html_url/pull/num|#num> from `head.ref` to `base.ref`"``

    Args:
        pr:
            Pull request dictionary describing an individual PR.
        html_url:
            HTML URL for the repository, used as the base for PR links.

    Returns:
        A formatted string as described above, or ``None`` if required
        data is missing.
    """
    if not html_url:
        return None

    number = pr.get("number")
    if number is None:
        return None

    head = pr.get("head") or {}
    base = pr.get("base") or {}

    head_ref = str(head.get("ref") or "").strip()
    base_ref = str(base.get("ref") or "").strip()

    link = f"{html_url}/pull/{number}"
    return f"<{link}|#{number}> from `{head_ref}` to `{base_ref}`"


def build_pull_request_string(workflow_run: Dict[str, Any]) -> str:
    """
    Build the pull request description string for internal PRs.

    Internal PRs are those whose base repository matches the repository
    of the workflow run. Each PR is rendered using
    :func:`_format_pull_request_segment`, and segments are joined with
    ``", "`` when multiple PRs exist.

    Args:
        workflow_run:
            Workflow run dictionary from the GitHub API.

    Returns:
        A formatted string describing internal PRs, or an empty string if
        none are present or formatted.
    """
    repository = workflow_run.get("repository") or {}
    repo_url = str(repository.get("url") or "")
    html_url = str(repository.get("html_url") or "")

    prs = _get_pull_requests(workflow_run)

    segments: List[str] = []
    for pr in prs:
        if not _is_internal_pull_request(pr, repo_url):
            continue
        segment = _format_pull_request_segment(pr, html_url)
        if segment:
            segments.append(segment)

    return ", ".join(segments)


def _workflow_duration_string(workflow_run: Dict[str, Any]) -> str:
    """
    Compute a duration string for the overall workflow run.

    Args:
        workflow_run:
            Workflow run metadata dictionary. The function reads the
            ``"created_at"`` and ``"updated_at"`` fields.

    Returns:
        A human-readable duration string (e.g. ``"1m 30s"``) or an empty
        string if the timestamps are unavailable or invalid.
    """
    created_at = parse_iso8601(workflow_run.get("created_at"))
    updated_at = parse_iso8601(workflow_run.get("updated_at"))
    if not (created_at and updated_at):
        return ""
    return compute_duration(created_at, updated_at)


def _extract_repo_context(workflow_run: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    """
    Extract repository and URL context used in Slack messages.

    Args:
        workflow_run:
            Workflow run dictionary from the GitHub API.

    Returns:
        A 5-tuple:

            ``(repo_full_name, repo_html_url, repo_url, branch_url, workflow_run_url)``

        where:

          - ``repo_full_name`` is the repository's full name (e.g. ``"owner/repo"``).
          - ``repo_html_url`` is the public HTML URL for the repo.
          - ``repo_url`` is the Slack-formatted footer link.
          - ``branch_url`` is a Slack-formatted link to the branch.
          - ``workflow_run_url`` is a Slack-formatted link to the workflow run.
    """
    repository = workflow_run.get("repository") or {}
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
        f"<{workflow_run_html_url}|#{run_number}>" if workflow_run_html_url and run_number else ""
    )

    return repo_full_name, repo_html_url, repo_url, branch_url, workflow_run_url


def _build_status_string(
    workflow_msg: str,
    actor: str,
    event_name: str,
    branch_url: str,
    workflow_run: Dict[str, Any],
) -> str:
    """
    Build the main status line for the Slack message.

    The default format is:

        ``"Success: actor's `push` on `branch`"``

    where the lead word (``"Success:"``, ``"Cancelled:"``, ``"Failed:"``)
    derives from :func:`determine_workflow_color_and_msg`.

    If one or more internal pull requests are associated with the run,
    the status line is overridden with a PR-specific variant:

        ``"Success: actor's `pull_request` <PR description>"``

    Args:
        workflow_msg:
            Lead word for the status line (e.g. ``"Success:"``).
        actor:
            Username of the GitHub actor (``GITHUB_ACTOR``).
        event_name:
            Name of the triggering event (``GITHUB_EVENT_NAME``).
        branch_url:
            Slack-formatted link to the branch, or plain branch name.
        workflow_run:
            Workflow run dictionary, used to derive PR information.

    Returns:
        A single formatted status line for inclusion in the Slack text block.
    """
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
    """
    Build the workflow details line for the Slack message.

    Typical format:

        ``"Workflow: CI <run_link|#14> completed in `1m 30s`"``

    Args:
        workflow_name:
            Name of the workflow (``GITHUB_WORKFLOW``).
        workflow_run_url:
            Slack-formatted link to the workflow run.
        workflow_duration:
            Human-readable workflow duration string.

    Returns:
        A formatted line describing the workflow name, run number and
        completion duration.
    """
    parts: List[str] = ["Workflow:"]
    if workflow_name:
        parts.append(workflow_name)
    if workflow_run_url:
        parts.append(workflow_run_url)

    details = " ".join(parts).strip()
    if workflow_duration:
        return f"{details} completed in `{workflow_duration}`"
    return f"{details} completed"


def _build_commit_message_text(head_commit_message: str, include_commit_message: bool) -> str:
    """
    Optionally build the commit message line for the Slack message.

    Args:
        head_commit_message:
            Commit message string extracted from ``workflow_run.head_commit``.
        include_commit_message:
            If ``True``, the line is included when a non-empty message is
            available. If ``False``, the line is omitted.

    Returns:
        ``"Commit: <message>"`` when enabled and non-empty, otherwise an
        empty string.
    """
    if not include_commit_message:
        return ""
    if not head_commit_message:
        return ""
    return f"Commit: {head_commit_message}"


def _apply_slack_cosmetics(payload: Dict[str, Any]) -> None:
    """
    Apply optional Slack cosmetic fields to the payload.

    The following environment variables are consulted (in order):

      - ``SEND_TO_SLACK_CHANNEL`` then ``SLACK_CHANNEL``
      - ``SEND_TO_SLACK_NAME`` then ``SLACK_NAME``
      - ``SEND_TO_SLACK_ICON_EMOJI`` then ``SLACK_ICON_EMOJI``
      - ``SEND_TO_SLACK_ICON_URL`` then ``SLACK_ICON_URL``

    Any values present are copied directly onto the payload.

    Args:
        payload:
            Mutable Slack payload dictionary, which is updated in-place.
    """
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
    """
    Build the complete Slack webhook payload for a workflow run.

    This function orchestrates:

      - High-level workflow status (colour and message).
      - Workflow metadata (actor, event, branch, run URL, duration).
      - Optional commit message line.
      - Per-job fields, when enabled via configuration.

    Args:
        workflow_run:
            Workflow run dictionary from the GitHub API.
        completed_jobs:
            List of completed job dictionaries.
        include_jobs_mode:
            Include mode for per-job fields. See
            :func:`_should_include_jobs` for details.
        include_commit_message:
            Whether to include a commit message line when available.

    Returns:
        A dictionary representing the Slack webhook payload, ready to be
        JSON-encoded and sent to the Incoming Webhook.
    """
    workflow_color, workflow_msg = determine_workflow_color_and_msg(completed_jobs)
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
    """
    Send a JSON payload to a Slack Incoming Webhook.

    Args:
        webhook_url:
            Slack Incoming Webhook URL.
        payload:
            Dictionary to be JSON-encoded and posted to the webhook.

    Raises:
        SystemExit:
            If the HTTP response status is not in the 2xx range, or if a
            network / unexpected error occurs.
    """
    try:
        body = json.dumps(payload).encode("utf-8")
    except (TypeError, ValueError) as exc:
        error(f"Failed to serialise Slack payload as JSON: {exc}", code=1)

    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(webhook_url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            _ = resp.read()  # Response body is typically empty; read and discard.
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
    Script entry point for use in GitHub Actions.

    High-level workflow:

      1. Read configuration from environment variables.
      2. Fetch workflow run metadata and jobs from the GitHub API.
      3. Determine whether a Slack notification should be sent based on
         ``SEND_TO_SLACK_RESULTS`` and the workflow conclusion.
      4. Optionally filter out ignored jobs from the per-job fields using
         ``SEND_TO_SLACK_IGNORE_JOBS``.
      5. Build a Slack payload mirroring Gamesight's formatting.
      6. POST the payload to ``SLACK_WEBHOOK_URL``.

    Expected environment variables are described in the module-level
    docstring.

    Raises:
        SystemExit:
            On misconfiguration, GitHub API failure, Slack webhook failure,
            or other unrecoverable errors.
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
        print(
            f"Warning: SEND_TO_SLACK_JOBS_TO_FETCH={jobs_to_fetch_raw!r} is not an integer; "
            "defaulting to 30.",
            file=sys.stderr,
        )
        jobs_to_fetch = 30

    workflow_run, completed_jobs = fetch_run_and_jobs(repo, run_id, token, jobs_to_fetch)
    workflow_conclusion = get_workflow_conclusion(workflow_run)

    # Determine whether this workflow conclusion should trigger a Slack message.
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

    # Optional: list of jobs to ignore in the per-job Slack fields.
    raw_ignored_jobs = os.environ.get("SEND_TO_SLACK_IGNORE_JOBS", "")
    ignored_job_names: Optional[Set[str]] = None
    if raw_ignored_jobs.strip():
        ignored_job_names = parse_ignored_jobs(raw_ignored_jobs)

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
