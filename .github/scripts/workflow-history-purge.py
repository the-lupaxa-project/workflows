#!/usr/bin/env python3
"""
Purge GitHub Actions workflow history for the current repository.

This script is designed to run inside GitHub Actions. It deletes completed
workflow runs from the GitHub REST API while deliberately skipping active,
queued, requested, waiting and pending runs. In delete mode it repeatedly
fetches page 1 because deleting runs changes GitHub's paginated result set.

Configuration is provided through environment variables so this script can be
used from a reusable workflow without command-line arguments.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, NoReturn, Optional, Tuple
from urllib.error import HTTPError, URLError


DEFAULT_PER_PAGE = 100
DEFAULT_LIMIT = 0
DEFAULT_DELETE_SLEEP_SECONDS = 0.25
DEFAULT_RETRIES = 3
DEFAULT_VERBOSITY = 1

VALID_VERBOSITY = {0, 1, 2}
SKIPPED_STATUSES = {"in_progress", "queued", "waiting", "requested", "pending"}

EMOJI_PURGE = "🧨"
EMOJI_DELETE = "🔥"
EMOJI_SKIP = "⏭️"
EMOJI_WARNING = "⚠️"
EMOJI_SUCCESS = "✅"
EMOJI_RUN = "🏃"
EMOJI_SUMMARY = "📊"
EMOJI_SLEEP = "⏱️"
EMOJI_RETRY = "🔁"
EMOJI_CONFIRM = "☑️"

Run = Dict[str, Any]


@dataclass
class Stats:
    """Runtime statistics for the purge operation."""

    inspected: int = 0
    candidates: int = 0
    deleted: int = 0
    skipped: int = 0
    failed: int = 0
    retries: int = 0
    passes: int = 0


def log(message: str = "") -> None:
    """Print a message to stdout."""
    print(message, flush=True)


def error(message: str, *, code: int = 1) -> NoReturn:
    """Print a formatted error message and terminate the script."""
    print(f"{EMOJI_WARNING} ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def env_value(name: str, default: str = "") -> str:
    """Read an environment variable as a string."""
    return os.environ.get(name, default)


def github_token_from_env() -> str:
    """Return the first supported GitHub API token found in the environment."""
    return (
        env_value("GITHUB_TOKEN")
        or env_value("GH_TOKEN")
        or env_value("ACTIONS_RUNTIME_TOKEN")
    )


def parse_bool(value: str, *, default: bool) -> bool:
    """Parse a permissive boolean string."""
    if value == "":
        return default

    value = value.strip().lower()

    if value in ("1", "true", "yes", "y", "on"):
        return True

    if value in ("0", "false", "no", "n", "off"):
        return False

    return default


def parse_int(value: str, *, default: int) -> int:
    """Parse an integer, returning the default on empty or invalid input."""
    if value == "":
        return default

    try:
        return int(value)
    except ValueError:
        return default


def parse_float(value: str, *, default: float) -> float:
    """Parse a float, returning the default on empty or invalid input."""
    if value == "":
        return default

    try:
        return float(value)
    except ValueError:
        return default


def parse_next_link(link_header: str) -> Optional[str]:
    """Extract the next-page URL from a GitHub API Link header."""
    if not link_header:
        return None

    for part in link_header.split(","):
        section = part.strip()

        if 'rel="next"' not in section:
            continue

        start = section.find("<")
        end = section.find(">")

        if start != -1 and end != -1 and end > start:
            return section[start + 1 : end]

    return None


def github_headers(token: str) -> Dict[str, str]:
    """Build headers for GitHub REST API requests."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-workflow-history-purge",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def decode_http_error(exc: HTTPError) -> str:
    """Read and decode an HTTPError response body."""
    if not hasattr(exc, "read"):
        return ""

    return exc.read().decode("utf-8", errors="replace")


def parse_github_json(body: bytes, url: str) -> Dict[str, Any]:
    """Decode a GitHub API JSON response and require a top-level object."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode JSON from {url}: {exc}")

    if not isinstance(data, dict):
        error(f"GitHub API response from {url} was not an object.")

    return data


def retry_sleep_seconds(attempt: int) -> int:
    """Return the retry backoff duration for an attempt number."""
    return min(60, 2**attempt * 5)


def github_request(
    url: str,
    token: str,
    *,
    method: str = "GET",
    retries: int,
    stats: Stats,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """Send a request to the GitHub REST API with retry handling."""
    transient_http_statuses = {403, 429, 500, 502, 503, 504}

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=github_headers(token), method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.getcode()
                body = resp.read()
                next_url = parse_next_link(resp.headers.get("Link", ""))

                if method == "DELETE":
                    return None, None, status

                if not (200 <= status < 300):
                    error(f"GitHub API returned HTTP {status} for {method} {url}")

                return parse_github_json(body, url), next_url, status

        except HTTPError as exc:
            body_text = decode_http_error(exc)

            if exc.code in transient_http_statuses and attempt < retries:
                stats.retries += 1
                sleep_for = retry_sleep_seconds(attempt)
                log(
                    f"{EMOJI_RETRY} [RETRY] {method} {url} failed with HTTP {exc.code}; "
                    f"retrying in {sleep_for}s"
                )
                time.sleep(sleep_for)
                continue

            if body_text:
                print(body_text, file=sys.stderr, flush=True)
            error(f"GitHub API returned HTTP {exc.code} for {method} {url}: {exc.reason}")

        except URLError as exc:
            if attempt < retries:
                stats.retries += 1
                sleep_for = retry_sleep_seconds(attempt)
                log(
                    f"{EMOJI_RETRY} [RETRY] {method} {url} failed: {exc.reason}; "
                    f"retrying in {sleep_for}s"
                )
                time.sleep(sleep_for)
                continue

            error(f"Failed to reach GitHub API at {url}: {exc.reason}")

    error(f"GitHub API request failed after retries for {method} {url}")


def validate_non_negative(name: str, value: int) -> None:
    """Validate that an integer is zero or greater."""
    if value < 0:
        error(f"{name} must be 0 or greater.", code=2)


def validate_float_non_negative(name: str, value: float) -> None:
    """Validate that a float is zero or greater."""
    if value < 0:
        error(f"{name} must be 0 or greater.", code=2)


def required_runtime_context() -> Tuple[str, str, str]:
    """Read and validate required GitHub Actions runtime context."""
    repo = env_value("GITHUB_REPOSITORY").strip()
    token = github_token_from_env()
    current_run_id = env_value("GITHUB_RUN_ID").strip()

    if not repo:
        error("GITHUB_REPOSITORY is required.", code=2)

    if not token:
        error("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is required.", code=2)

    return repo, token, current_run_id


def read_config_from_env() -> Dict[str, Any]:
    """Read, parse and validate purge configuration from environment variables."""
    dry_run = parse_bool(env_value("PURGE_DRY_RUN"), default=True)
    confirm = parse_bool(env_value("PURGE_CONFIRM"), default=False)
    limit = parse_int(env_value("PURGE_LIMIT"), default=DEFAULT_LIMIT)
    delete_sleep_seconds = parse_float(
        env_value("PURGE_DELAY_SECONDS"),
        default=DEFAULT_DELETE_SLEEP_SECONDS,
    )
    verbosity = parse_int(env_value("PURGE_VERBOSITY"), default=DEFAULT_VERBOSITY)
    retries = parse_int(env_value("PURGE_RETRIES"), default=DEFAULT_RETRIES)

    validate_non_negative("PURGE_LIMIT", limit)
    validate_float_non_negative("PURGE_DELAY_SECONDS", delete_sleep_seconds)
    validate_non_negative("PURGE_RETRIES", retries)

    if verbosity not in VALID_VERBOSITY:
        verbosity = DEFAULT_VERBOSITY

    if not dry_run and not confirm:
        error(
            "Refusing to delete workflow runs without PURGE_CONFIRM=true when PURGE_DRY_RUN=false.",
            code=2,
        )

    return {
        f"{EMOJI_PURGE} Mode": "DRY RUN" if dry_run else "DELETE",
        f"{EMOJI_CONFIRM} Confirm": confirm,
        f"{EMOJI_RUN} Limit": limit,
        f"{EMOJI_SLEEP} Delete sleep seconds": delete_sleep_seconds,
        f"{EMOJI_RETRY} Retries": retries,
        "Verbosity": verbosity,
    }


def config_value(config: Dict[str, Any], key_suffix: str) -> Any:
    """Return a config value by matching the end of its display key."""
    for key, value in config.items():
        if key.endswith(key_suffix):
            return value

    error(f"Internal configuration key not found: {key_suffix}")


def dry_run_enabled(config: Dict[str, Any]) -> bool:
    """Return whether purge is running in dry-run mode."""
    return config_value(config, "Mode") == "DRY RUN"


def print_config(config: Dict[str, Any]) -> None:
    """Print the active purge configuration."""
    log(f"{EMOJI_PURGE} Workflow History Purge")
    log("=========================")

    for key, value in config.items():
        if key == "Verbosity":
            continue
        log(f"{key}: {value}")

    log("")


def workflow_runs_page_url(repo: str, *, page: int = 1) -> str:
    """Build a workflow runs API page URL."""
    query = urllib.parse.urlencode({"per_page": DEFAULT_PER_PAGE, "page": page})
    return f"https://api.github.com/repos/{repo}/actions/runs?{query}"


def fetch_workflow_runs_page(
    repo: str,
    token: str,
    *,
    page: int,
    retries: int,
    stats: Stats,
) -> List[Run]:
    """Fetch one page of workflow runs."""
    url = workflow_runs_page_url(repo, page=page)
    data, _next_url, _status = github_request(url, token, retries=retries, stats=stats)

    if data is None:
        return []

    workflow_runs = data.get("workflow_runs", [])
    if not isinstance(workflow_runs, list):
        return []

    return [run for run in workflow_runs if isinstance(run, dict)]


def fetch_all_workflow_runs(repo: str, token: str, *, retries: int, stats: Stats) -> List[Run]:
    """Fetch all workflow runs using Link-header pagination."""
    runs: List[Run] = []
    next_url: Optional[str] = f"https://api.github.com/repos/{repo}/actions/runs?per_page={DEFAULT_PER_PAGE}"

    while next_url:
        data, next_url, _status = github_request(next_url, token, retries=retries, stats=stats)

        if data is None:
            break

        page_runs = data.get("workflow_runs", [])
        if isinstance(page_runs, list):
            runs.extend(run for run in page_runs if isinstance(run, dict))

        log(f"{EMOJI_RUN} [FETCH] Loaded {len(runs)} workflow runs so far")

    return runs


def run_id_as_int(run: Run) -> Optional[int]:
    """Return the workflow run ID when it is an integer."""
    run_id = run.get("id")

    if isinstance(run_id, int):
        return run_id

    return None


def run_status(run: Run) -> str:
    """Return the normalised workflow run status."""
    return str(run.get("status") or "").strip().lower()


def run_conclusion(run: Run) -> str:
    """Return the normalised workflow run conclusion."""
    return str(run.get("conclusion") or "").strip().lower()


def run_name(run: Run) -> str:
    """Return the workflow run display name."""
    return str(run.get("name") or "unknown")


def run_created_at(run: Run) -> str:
    """Return the workflow run creation timestamp."""
    return str(run.get("created_at") or "unknown")


def delete_workflow_run(repo: str, run_id: int, token: str, retries: int, stats: Stats) -> None:
    """Delete one workflow run through the GitHub API."""
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    _data, _next_url, status = github_request(
        url,
        token,
        method="DELETE",
        retries=retries,
        stats=stats,
    )

    if status not in (202, 204):
        error(f"Unexpected HTTP {status} deleting workflow run {run_id}")


def should_skip_run(run: Run, current_run_id: str) -> Tuple[bool, str]:
    """Return whether a workflow run should be skipped and why."""
    run_id = str(run.get("id") or "")
    status = run_status(run)

    if current_run_id and run_id == current_run_id:
        return True, "current workflow run"

    if status in SKIPPED_STATUSES:
        return True, f"active status: {status}"

    if status != "completed":
        return True, f"unsupported status: {status or 'unknown'}"

    return False, ""


def log_run_action(action: str, run: Run, reason: str, count: int, verbosity: int) -> None:
    """Log one workflow run action if permitted by verbosity."""
    if verbosity == 0:
        return

    if action in {"SKIP", "LIMIT"} and verbosity < 2:
        return

    run_id = str(run.get("id") or "unknown")
    status = run_status(run) or "unknown"
    conclusion = run_conclusion(run) or "none"
    name = run_name(run)
    created_at = run_created_at(run)

    if verbosity >= 2:
        log(
            f"{EMOJI_RUN} [{action}] {count:>5} | {run_id} | {created_at} | "
            f"{name} | {status}/{conclusion} | {reason}"
        )
        return

    emoji = EMOJI_DELETE if action in {"DELETE", "DRY"} else EMOJI_SKIP
    log(f"{emoji} [{action}] {count:>5} | {run_id} | {conclusion:<12} | {name}")


def handle_run(
    *,
    repo: str,
    token: str,
    run: Run,
    config: Dict[str, Any],
    stats: Stats,
    current_run_id: str,
) -> bool:
    """Inspect and optionally delete one workflow run."""
    stats.inspected += 1

    verbosity = int(config_value(config, "Verbosity"))
    limit = int(config_value(config, "Limit"))
    retries = int(config_value(config, "Retries"))
    dry_run = dry_run_enabled(config)
    delete_sleep_seconds = float(config_value(config, "Delete sleep seconds"))

    should_skip, reason = should_skip_run(run, current_run_id)
    if should_skip:
        stats.skipped += 1
        log_run_action("SKIP", run, reason, stats.candidates, verbosity)
        return False

    if limit and stats.candidates >= limit:
        stats.skipped += 1
        log_run_action("LIMIT", run, "delete limit reached", stats.candidates, verbosity)
        return False

    stats.candidates += 1

    if dry_run:
        stats.skipped += 1
        log_run_action("DRY", run, "dry run", stats.candidates, verbosity)
        return False

    run_id = run_id_as_int(run)
    if run_id is None:
        stats.failed += 1
        log_run_action("FAILED", run, "invalid workflow run id", stats.candidates, verbosity)
        return False

    try:
        delete_workflow_run(repo, run_id, token, retries, stats)
        stats.deleted += 1
        log_run_action("DELETE", run, "deleted", stats.candidates, verbosity)

        if delete_sleep_seconds:
            time.sleep(delete_sleep_seconds)

        return True
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - keep purge resilient across individual delete failures.
        stats.failed += 1
        print(
            f"{EMOJI_WARNING} [FAILED] {run_id} | {run_name(run)} | {exc}",
            file=sys.stderr,
            flush=True,
        )
        return False


def run_dry_run(repo: str, token: str, current_run_id: str, config: Dict[str, Any], stats: Stats) -> None:
    """Inspect all workflow runs without deleting anything."""
    retries = int(config_value(config, "Retries"))
    runs = fetch_all_workflow_runs(repo, token, retries=retries, stats=stats)

    for run in runs:
        handle_run(
            repo=repo,
            token=token,
            run=run,
            config=config,
            stats=stats,
            current_run_id=current_run_id,
        )


def run_delete(repo: str, token: str, current_run_id: str, config: Dict[str, Any], stats: Stats) -> None:
    """Delete workflow runs by repeatedly processing the first API page."""
    retries = int(config_value(config, "Retries"))
    limit = int(config_value(config, "Limit"))
    verbosity = int(config_value(config, "Verbosity"))

    while True:
        if limit and stats.candidates >= limit:
            break

        stats.passes += 1
        runs = fetch_workflow_runs_page(repo, token, page=1, retries=retries, stats=stats)

        if verbosity >= 1:
            log(f"{EMOJI_SUMMARY} [PASS {stats.passes}] Retrieved {len(runs)} workflow runs")

        if not runs:
            break

        deleted_this_pass = 0
        completed_seen_this_pass = 0

        for run in runs:
            if limit and stats.candidates >= limit:
                break

            if run_status(run) == "completed":
                completed_seen_this_pass += 1

            if handle_run(
                repo=repo,
                token=token,
                run=run,
                config=config,
                stats=stats,
                current_run_id=current_run_id,
            ):
                deleted_this_pass += 1

        if deleted_this_pass > 0:
            continue

        if completed_seen_this_pass == 0:
            break

        log(
            f"{EMOJI_WARNING} [STOP] No deletions completed during this pass; "
            "stopping to avoid an infinite loop."
        )
        break


def print_summary(repo: str, config: Dict[str, Any], stats: Stats, started: datetime) -> None:
    """Print the final purge summary."""
    elapsed = datetime.now(timezone.utc) - started

    log("")
    log(f"{EMOJI_SUMMARY} Summary")
    log("-------")
    log(f"Repository : {repo}")
    log(f"Mode       : {config_value(config, 'Mode')}")
    log(f"Confirm    : {config_value(config, 'Confirm')}")
    log(f"Inspected  : {stats.inspected}")
    log(f"Candidates : {stats.candidates}")
    log(f"Deleted    : {stats.deleted}")
    log(f"Skipped    : {stats.skipped}")
    log(f"Failed     : {stats.failed}")
    log(f"Retries    : {stats.retries}")
    log(f"Passes     : {stats.passes}")
    log(f"Limit      : {config_value(config, 'Limit') or 'unlimited'}")
    log(f"Elapsed    : {str(elapsed).split('.')[0]}")


def main() -> None:
    """Run the workflow history purge."""
    repo, token, current_run_id = required_runtime_context()
    config = read_config_from_env()
    started = datetime.now(timezone.utc)
    stats = Stats()

    if int(config_value(config, "Verbosity")) != 0:
        print_config(config)

    if dry_run_enabled(config):
        run_dry_run(repo, token, current_run_id, config, stats)
    else:
        run_delete(repo, token, current_run_id, config, stats)

    print_summary(repo, config, stats, started)

    if stats.failed:
        raise SystemExit(1)

    log(f"{EMOJI_SUCCESS} Workflow history purge complete")


if __name__ == "__main__":
    main()
