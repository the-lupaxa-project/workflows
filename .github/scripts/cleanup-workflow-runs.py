#!/usr/bin/env python3
"""
Clean up old GitHub Actions workflow runs and optionally old artifacts.

This script is designed to run inside GitHub Actions. It fetches workflow runs
from the GitHub REST API, applies retention and preservation rules, optionally
deletes selected runs and artifacts, and writes a Markdown report.

Configuration is provided through environment variables so this script can be
used from a reusable workflow without command-line arguments.
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple
from urllib.error import HTTPError, URLError


DEFAULT_RETENTION_DAYS = 90
DEFAULT_ARTIFACT_RETENTION_DAYS = 90
DEFAULT_PER_PAGE = 100
DEFAULT_MAX_DELETES_PER_RUN = 250
DEFAULT_MAX_ARTIFACT_DELETES_PER_RUN = 250
DEFAULT_DELETE_SLEEP_SECONDS = 1.0
DEFAULT_PROGRESS_EVERY = 50
DEFAULT_PRESERVE_BRANCH = "master"
DEFAULT_VERBOSITY = "normal"

VALID_VERBOSITY = {"quiet", "normal", "verbose"}

EMOJI_CLEANUP = "🧹"
EMOJI_DELETE = "🔥"
EMOJI_KEEP = "🛡️"
EMOJI_SKIP = "⏭️"
EMOJI_WARNING = "⚠️"
EMOJI_SUCCESS = "✅"
EMOJI_ARTIFACT = "📦"
EMOJI_RUN = "🏃"
EMOJI_BRANCH = "🌿"
EMOJI_STAR = "⭐"
EMOJI_SUMMARY = "📊"
EMOJI_SLEEP = "⏱️"
EMOJI_VERBOSITY = "🔊"

Run = Dict[str, Any]
Artifact = Dict[str, Any]
Config = Dict[str, Any]
ActionRow = Dict[str, str]
WorkflowTotals = Dict[str, Dict[str, int]]


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


def parse_iso8601(value: str) -> Optional[datetime]:
    """Parse a GitHub-style ISO 8601 timestamp as UTC."""
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


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


def slugify(value: str, *, fallback: str = "unknown") -> str:
    """Convert a string into a filesystem-friendly slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-._")

    return value or fallback


def md_value(value: str) -> str:
    """Escape a value so it can be safely rendered inside a Markdown table."""
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("|", "\\|")
    value = value.replace("\r", " ")
    value = value.replace("\n", " ")

    return value.strip()


def action_emoji(action: str) -> str:
    """Return the emoji associated with a report action."""
    if action == "DELETE":
        return EMOJI_DELETE

    if action == "KEEP":
        return EMOJI_KEEP

    return EMOJI_SKIP


def github_headers(token: str) -> Dict[str, str]:
    """Build headers for GitHub REST API requests."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-cleanup-workflow-runs",
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


def github_request(
    url: str,
    token: str,
    *,
    method: str = "GET",
) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """Send a request to the GitHub REST API."""
    req = urllib.request.Request(url, headers=github_headers(token), method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body = resp.read()
            next_url = parse_next_link(resp.headers.get("Link", ""))
    except HTTPError as exc:
        body_text = decode_http_error(exc)
        if body_text:
            print(body_text, file=sys.stderr, flush=True)
        error(f"GitHub API returned HTTP {exc.code} for {method} {url}: {exc.reason}")
    except URLError as exc:
        error(f"Failed to reach GitHub API at {url}: {exc.reason}")

    if method == "DELETE":
        return None, None, status

    if not (200 <= status < 300):
        error(f"GitHub API returned HTTP {status} for {method} {url}")

    return parse_github_json(body, url), next_url, status


def fetch_paginated_items(
    url: str,
    token: str,
    *,
    collection_key: str,
    emoji: str,
    label: str,
) -> List[Dict[str, Any]]:
    """Fetch all dictionary items from a paginated GitHub API collection."""
    items: List[Dict[str, Any]] = []
    next_url: Optional[str] = url

    while next_url:
        data, next_url, _status = github_request(next_url, token)

        if data is None:
            break

        page_items = data.get(collection_key, [])

        if isinstance(page_items, list):
            items.extend(item for item in page_items if isinstance(item, dict))

        log(f"{emoji} [FETCH] Loaded {len(items)} {label} so far")

    return items


def fetch_all_workflow_runs(repo: str, token: str) -> List[Run]:
    """Fetch all workflow runs for a repository."""
    url = f"https://api.github.com/repos/{repo}/actions/runs?per_page={DEFAULT_PER_PAGE}"

    return fetch_paginated_items(
        url,
        token,
        collection_key="workflow_runs",
        emoji=EMOJI_RUN,
        label="workflow runs",
    )


def fetch_all_artifacts(repo: str, token: str) -> List[Artifact]:
    """Fetch all workflow artifacts for a repository."""
    url = f"https://api.github.com/repos/{repo}/actions/artifacts?per_page={DEFAULT_PER_PAGE}"

    return fetch_paginated_items(
        url,
        token,
        collection_key="artifacts",
        emoji=EMOJI_ARTIFACT,
        label="artifacts",
    )


def workflow_key(run: Run) -> str:
    """Return a stable grouping key for a workflow run."""
    workflow_id = run.get("workflow_id")
    if workflow_id is not None:
        return str(workflow_id)

    path = str(run.get("path") or "")
    if path:
        return path

    return str(run.get("name") or "unknown")


def workflow_display(run: Run) -> str:
    """Return a human-readable workflow name for reports."""
    name = str(run.get("name") or "unknown")
    path = str(run.get("path") or "")

    if path:
        return f"{name} ({path})"

    return name


def run_created_at(run: Run) -> datetime:
    """Return the workflow run creation time, falling back to the Unix epoch."""
    created_at = parse_iso8601(str(run.get("created_at") or ""))

    if created_at:
        return created_at

    return datetime.fromtimestamp(0, timezone.utc)


def artifact_created_at(artifact: Artifact) -> datetime:
    """Return the artifact creation time, falling back to the Unix epoch."""
    created_at = parse_iso8601(str(artifact.get("created_at") or ""))

    if created_at:
        return created_at

    return datetime.fromtimestamp(0, timezone.utc)


def run_id_as_int(run: Run) -> Optional[int]:
    """Return the workflow run ID when it is an integer."""
    run_id = run.get("id")

    if isinstance(run_id, int):
        return run_id

    return None


def artifact_id_as_int(artifact: Artifact) -> Optional[int]:
    """Return the artifact ID when it is an integer."""
    artifact_id = artifact.get("id")

    if isinstance(artifact_id, int):
        return artifact_id

    return None


def run_status(run: Run) -> str:
    """Return the normalised workflow run status."""
    return str(run.get("status") or "").strip().lower()


def run_conclusion(run: Run) -> str:
    """Return the normalised workflow run conclusion."""
    return str(run.get("conclusion") or "").strip().lower()


def run_head_branch(run: Run) -> str:
    """Return the workflow run head branch."""
    return str(run.get("head_branch") or "").strip()


def keep_latest_by_conclusion(
    runs: List[Run],
    conclusion: str,
    keep_ids: Set[int],
) -> None:
    """Add the newest run matching a conclusion to the preserved run IDs."""
    for run in runs:
        if run_conclusion(run) != conclusion:
            continue

        run_id = run_id_as_int(run)
        if run_id is not None:
            keep_ids.add(run_id)

        return


def keep_last_n_by_conclusion(
    runs: List[Run],
    conclusion: str,
    count: int,
    keep_ids: Set[int],
) -> None:
    """Add the newest N runs matching a conclusion to the preserved run IDs."""
    kept = 0

    for run in runs:
        if run_conclusion(run) != conclusion:
            continue

        run_id = run_id_as_int(run)
        if run_id is not None:
            keep_ids.add(run_id)
            kept += 1

        if kept >= count:
            return


def group_preserved_branch_runs(runs: List[Run], preserve_branch: str) -> Dict[str, List[Run]]:
    """Group completed runs on the preserved branch by workflow."""
    grouped: Dict[str, List[Run]] = {}

    for run in runs:
        if run_status(run) != "completed":
            continue

        if run_head_branch(run) != preserve_branch:
            continue

        grouped.setdefault(workflow_key(run), []).append(run)

    return grouped


def find_keep_run_ids(
    runs: List[Run],
    *,
    preserve_branch: str,
    keep_latest_successful: bool,
    keep_latest_failed: bool,
    keep_latest_cancelled: bool,
    keep_latest_timed_out: bool,
    keep_last_n_successful: int,
) -> Set[int]:
    """Find representative workflow run IDs that must be preserved."""
    keep_ids: Set[int] = set()
    grouped = group_preserved_branch_runs(runs, preserve_branch)

    for workflow_runs in grouped.values():
        completed_sorted = sorted(workflow_runs, key=run_created_at, reverse=True)

        if keep_latest_successful:
            keep_latest_by_conclusion(completed_sorted, "success", keep_ids)

        if keep_latest_failed:
            keep_latest_by_conclusion(completed_sorted, "failure", keep_ids)

        if keep_latest_cancelled:
            keep_latest_by_conclusion(completed_sorted, "cancelled", keep_ids)

        if keep_latest_timed_out:
            keep_latest_by_conclusion(completed_sorted, "timed_out", keep_ids)

        if keep_last_n_successful > 0:
            keep_last_n_by_conclusion(
                completed_sorted,
                "success",
                keep_last_n_successful,
                keep_ids,
            )

    return keep_ids


def should_delete_run(
    run: Run,
    *,
    cutoff: datetime,
    current_run_id: str,
    keep_run_ids: Set[int],
    preserve_branch: str,
    force_delete_non_default_branch: bool,
    delete_skipped: bool,
    delete_neutral: bool,
) -> Tuple[bool, str]:
    """Decide whether a workflow run should be deleted."""
    run_id = run.get("id")
    status = run_status(run)
    conclusion = run_conclusion(run)
    branch = run_head_branch(run)

    if str(run_id) == current_run_id:
        return False, "current cleanup run"

    if status != "completed":
        return False, f"not completed: {status}"

    if force_delete_non_default_branch and branch != preserve_branch:
        return True, f"force delete non-default branch: {branch}"

    if isinstance(run_id, int) and run_id in keep_run_ids:
        return False, "preserved representative run"

    if conclusion == "skipped" and not delete_skipped:
        return False, "skipped deletion disabled"

    if conclusion == "neutral" and not delete_neutral:
        return False, "neutral deletion disabled"

    if run_created_at(run) >= cutoff:
        return False, "newer than cutoff"

    return True, "old completed run"


def should_delete_artifact(
    artifact: Artifact,
    *,
    artifact_cutoff: datetime,
) -> Tuple[bool, str]:
    """Decide whether an artifact should be deleted."""
    expired = artifact.get("expired")

    if expired is True:
        return True, "artifact already expired"

    if artifact_created_at(artifact) >= artifact_cutoff:
        return False, "artifact newer than cutoff"

    return True, "old artifact"


def delete_workflow_run(repo: str, run_id: int, token: str) -> None:
    """Delete one workflow run through the GitHub API."""
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    _data, _next_url, status = github_request(url, token, method="DELETE")

    if status not in (202, 204):
        error(f"Unexpected HTTP {status} deleting workflow run {run_id}")


def delete_artifact(repo: str, artifact_id: int, token: str) -> None:
    """Delete one workflow artifact through the GitHub API."""
    url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}"
    _data, _next_url, status = github_request(url, token, method="DELETE")

    if status not in (202, 204):
        error(f"Unexpected HTTP {status} deleting artifact {artifact_id}")


def default_report_filename(repo: str) -> str:
    """Build the default Markdown cleanup report filename."""
    run_id = env_value("GITHUB_RUN_ID", "unknown")
    run_attempt = env_value("GITHUB_RUN_ATTEMPT", "1")
    repo_slug = slugify(repo.replace("/", "-"))

    return f"cleanup-workflow-runs-{repo_slug}-{run_id}-attempt-{run_attempt}.md"


def report_paths(repo: str) -> List[Path]:
    """Return all paths where the Markdown cleanup report should be written."""
    paths: List[Path] = []

    report_file = env_value("CLEANUP_WORKFLOW_RUNS_REPORT_FILE").strip()
    if not report_file:
        report_file = default_report_filename(repo)
        os.environ["CLEANUP_WORKFLOW_RUNS_REPORT_FILE"] = report_file

    paths.append(Path(report_file))

    step_summary = env_value("GITHUB_STEP_SUMMARY").strip()
    if step_summary:
        step_summary_path = Path(step_summary)
        if step_summary_path not in paths:
            paths.append(step_summary_path)

    return paths


def report_mode(path: Path) -> str:
    """Return the file mode for a report path."""
    step_summary = env_value("GITHUB_STEP_SUMMARY").strip()

    return "a" if str(path) == step_summary else "w"


def write_table_rows(rows: Dict[str, Any], out: Any) -> None:
    """Write key/value rows to a Markdown table."""
    for key, value in rows.items():
        print(f"| {md_value(key)} | {md_value(str(value))} |", file=out)


def write_summary_section(summary: Dict[str, Any], out: Any) -> None:
    """Write the report summary section."""
    print(f"## {EMOJI_SUMMARY} Summary", file=out)
    print(file=out)
    print("| Field | Value |", file=out)
    print("| :---- | :---- |", file=out)
    write_table_rows(summary, out)
    print(file=out)


def write_config_section(config: Config, out: Any) -> None:
    """Write the cleanup configuration section."""
    print(f"## {EMOJI_STAR} Configuration", file=out)
    print(file=out)
    print("| Field | Value |", file=out)
    print("| :---- | :---- |", file=out)
    write_table_rows(config, out)
    print(file=out)


def write_workflow_totals_section(workflow_totals: WorkflowTotals, out: Any) -> None:
    """Write per-workflow delete and keep totals."""
    print(f"## {EMOJI_RUN} Per-workflow totals", file=out)
    print(file=out)
    print(f"| Workflow | {EMOJI_DELETE} Deleted | {EMOJI_KEEP} Kept |", file=out)
    print("| :------- | ---------: | ------: |", file=out)

    for workflow, totals in sorted(workflow_totals.items(), key=lambda item: item[0].casefold()):
        print(
            f"| {md_value(workflow)} | {totals.get('deleted', 0)} | {totals.get('kept', 0)} |",
            file=out,
        )

    print(file=out)


def write_run_actions_section(run_actions: List[ActionRow], out: Any) -> None:
    """Write the workflow run action table."""
    print(f"## {EMOJI_RUN} Workflow run actions", file=out)
    print(file=out)
    print("| Action | Run ID | Created | Workflow | Branch | Status | Reason |", file=out)
    print("| :----- | :----- | :------ | :------- | :----- | :----- | :----- |", file=out)

    for item in run_actions:
        action = item["action"]
        print(
            "| "
            f"{action_emoji(action)} {md_value(action)} | "
            f"{md_value(item['id'])} | "
            f"{md_value(item['created'])} | "
            f"{md_value(item['workflow'])} | "
            f"{EMOJI_BRANCH} {md_value(item['branch'])} | "
            f"{md_value(item['status'])} | "
            f"{md_value(item['reason'])} |",
            file=out,
        )

    print(file=out)


def write_artifact_actions_section(artifact_actions: List[ActionRow], out: Any) -> None:
    """Write the artifact action table when artifact cleanup was processed."""
    if not artifact_actions:
        return

    print(f"## {EMOJI_ARTIFACT} Artifact actions", file=out)
    print(file=out)
    print("| Action | Artifact ID | Created | Name | Size | Reason |", file=out)
    print("| :----- | :---------- | :------ | :--- | ---: | :----- |", file=out)

    for item in artifact_actions:
        action = item["action"]
        print(
            "| "
            f"{action_emoji(action)} {md_value(action)} | "
            f"{md_value(item['id'])} | "
            f"{md_value(item['created'])} | "
            f"{md_value(item['name'])} | "
            f"{md_value(item['size'])} | "
            f"{md_value(item['reason'])} |",
            file=out,
        )

    print(file=out)


def write_report_file(
    path: Path,
    config: Config,
    run_actions: List[ActionRow],
    artifact_actions: List[ActionRow],
    workflow_totals: WorkflowTotals,
    summary: Dict[str, Any],
) -> None:
    """Write the Markdown cleanup report to a single path."""
    with path.open(report_mode(path), encoding="utf-8") as out:
        print(f"# {EMOJI_CLEANUP} Workflow Run Cleanup Report", file=out)
        print(file=out)

        write_summary_section(summary, out)
        write_config_section(config, out)
        write_workflow_totals_section(workflow_totals, out)
        write_run_actions_section(run_actions, out)
        write_artifact_actions_section(artifact_actions, out)


def write_markdown_report(
    repo: str,
    config: Config,
    run_actions: List[ActionRow],
    artifact_actions: List[ActionRow],
    workflow_totals: WorkflowTotals,
    summary: Dict[str, Any],
) -> None:
    """Write the cleanup report to all configured destinations."""
    for path in report_paths(repo):
        write_report_file(
            path=path,
            config=config,
            run_actions=run_actions,
            artifact_actions=artifact_actions,
            workflow_totals=workflow_totals,
            summary=summary,
        )


def print_config(config: Config) -> None:
    """Print the cleanup configuration to stdout."""
    log(f"{EMOJI_CLEANUP} Workflow run cleanup configuration")
    log("==================================")

    for key, value in config.items():
        log(f"{key}: {value}")

    log()


def should_log_action(verbosity: str, action: str) -> bool:
    """Return whether an action should be logged for the selected verbosity."""
    if verbosity == "quiet":
        return False

    if verbosity == "normal":
        return action == "DELETE"

    return True


def required_runtime_context() -> Tuple[str, str, str]:
    """Read and validate required GitHub Actions runtime context."""
    repo = env_value("GITHUB_REPOSITORY").strip()
    token = github_token_from_env()
    current_run_id = env_value("GITHUB_RUN_ID").strip()

    if not repo:
        error("GITHUB_REPOSITORY is required.")

    if not token:
        error("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is required.")

    return repo, token, current_run_id


def parse_verbosity() -> str:
    """Parse cleanup log verbosity."""
    verbosity = env_value("CLEANUP_WORKFLOW_RUNS_VERBOSITY", DEFAULT_VERBOSITY).strip().lower()

    if verbosity not in VALID_VERBOSITY:
        return DEFAULT_VERBOSITY

    return verbosity


def validate_minimum(name: str, value: int, minimum: int) -> None:
    """Validate that an integer is greater than or equal to a minimum."""
    if value < minimum:
        error(f"{name} must be at least {minimum}.")


def validate_non_negative(name: str, value: int) -> None:
    """Validate that an integer is zero or greater."""
    if value < 0:
        error(f"{name} must be 0 or greater.")


def validate_float_non_negative(name: str, value: float) -> None:
    """Validate that a float is zero or greater."""
    if value < 0:
        error(f"{name} must be 0 or greater.")


def read_config_from_env() -> Config:
    """Read, parse and validate cleanup configuration from environment variables."""
    retention_days = parse_int(
        env_value("CLEANUP_WORKFLOW_RUNS_RETENTION_DAYS"),
        default=DEFAULT_RETENTION_DAYS,
    )
    validate_minimum("CLEANUP_WORKFLOW_RUNS_RETENTION_DAYS", retention_days, 14)

    artifact_retention_days = parse_int(
        env_value("CLEANUP_WORKFLOW_RUNS_ARTIFACT_RETENTION_DAYS"),
        default=DEFAULT_ARTIFACT_RETENTION_DAYS,
    )
    validate_minimum("CLEANUP_WORKFLOW_RUNS_ARTIFACT_RETENTION_DAYS", artifact_retention_days, 1)

    keep_last_n_successful = parse_int(
        env_value("CLEANUP_WORKFLOW_RUNS_KEEP_LAST_N_SUCCESSFUL"),
        default=3,
    )
    validate_non_negative("CLEANUP_WORKFLOW_RUNS_KEEP_LAST_N_SUCCESSFUL", keep_last_n_successful)

    max_deletes_per_run = parse_int(
        env_value("CLEANUP_WORKFLOW_RUNS_MAX_DELETES"),
        default=DEFAULT_MAX_DELETES_PER_RUN,
    )
    validate_non_negative("CLEANUP_WORKFLOW_RUNS_MAX_DELETES", max_deletes_per_run)

    max_artifact_deletes_per_run = parse_int(
        env_value("CLEANUP_WORKFLOW_RUNS_MAX_ARTIFACT_DELETES"),
        default=DEFAULT_MAX_ARTIFACT_DELETES_PER_RUN,
    )
    validate_non_negative("CLEANUP_WORKFLOW_RUNS_MAX_ARTIFACT_DELETES", max_artifact_deletes_per_run)

    delete_sleep_seconds = parse_float(
        env_value("CLEANUP_WORKFLOW_RUNS_DELETE_SLEEP_SECONDS"),
        default=DEFAULT_DELETE_SLEEP_SECONDS,
    )
    validate_float_non_negative("CLEANUP_WORKFLOW_RUNS_DELETE_SLEEP_SECONDS", delete_sleep_seconds)

    progress_every = parse_int(
        env_value("CLEANUP_WORKFLOW_RUNS_PROGRESS_EVERY"),
        default=DEFAULT_PROGRESS_EVERY,
    )
    validate_non_negative("CLEANUP_WORKFLOW_RUNS_PROGRESS_EVERY", progress_every)

    dry_run = parse_bool(env_value("CLEANUP_WORKFLOW_RUNS_DRY_RUN"), default=True)

    return {
        f"{EMOJI_CLEANUP} Mode": "DRY RUN" if dry_run else "DELETE",
        f"{EMOJI_RUN} Retention days": retention_days,
        f"{EMOJI_ARTIFACT} Artifact retention days": artifact_retention_days,
        f"{EMOJI_ARTIFACT} Cleanup artifacts": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_CLEANUP_ARTIFACTS"),
            default=False,
        ),
        f"{EMOJI_BRANCH} Preserve branch": env_value(
            "CLEANUP_WORKFLOW_RUNS_PRESERVE_BRANCH",
        ).strip()
        or DEFAULT_PRESERVE_BRANCH,
        f"{EMOJI_DELETE} Force delete non-default branch": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_FORCE_DELETE_NON_DEFAULT_BRANCH"),
            default=False,
        ),
        f"{EMOJI_KEEP} Keep latest successful": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_SUCCESSFUL"),
            default=True,
        ),
        f"{EMOJI_KEEP} Keep latest failed": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_FAILED"),
            default=True,
        ),
        f"{EMOJI_KEEP} Keep latest cancelled": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_CANCELLED"),
            default=True,
        ),
        f"{EMOJI_KEEP} Keep latest timed out": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_TIMED_OUT"),
            default=True,
        ),
        f"{EMOJI_KEEP} Keep last N successful": keep_last_n_successful,
        f"{EMOJI_DELETE} Delete skipped": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_DELETE_SKIPPED"),
            default=True,
        ),
        f"{EMOJI_DELETE} Delete neutral": parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_DELETE_NEUTRAL"),
            default=True,
        ),
        f"{EMOJI_DELETE} Max deletes per run": max_deletes_per_run,
        f"{EMOJI_ARTIFACT} Max artifact deletes per run": max_artifact_deletes_per_run,
        f"{EMOJI_SLEEP} Delete sleep seconds": delete_sleep_seconds,
        f"{EMOJI_SUMMARY} Progress every": progress_every,
        f"{EMOJI_VERBOSITY} Verbosity": parse_verbosity(),
    }


def config_value(config: Config, key_suffix: str) -> Any:
    """Return a config value by matching the end of its display key."""
    for key, value in config.items():
        if key.endswith(key_suffix):
            return value

    error(f"Internal configuration key not found: {key_suffix}")


def dry_run_enabled(config: Config) -> bool:
    """Return whether cleanup is running in dry-run mode."""
    return config_value(config, "Mode") == "DRY RUN"


def increment_workflow_total(workflow_totals: WorkflowTotals, workflow: str, action: str) -> None:
    """Increment per-workflow deleted or kept totals."""
    workflow_totals.setdefault(workflow, {"deleted": 0, "kept": 0})

    if action == "DELETE":
        workflow_totals[workflow]["deleted"] += 1
    else:
        workflow_totals[workflow]["kept"] += 1


def build_run_action_row(run: Run, action: str, reason: str) -> ActionRow:
    """Build one workflow run action row for the report."""
    status = run_status(run)
    conclusion = run_conclusion(run)

    return {
        "action": action,
        "id": str(run.get("id")),
        "created": str(run.get("created_at") or ""),
        "workflow": workflow_display(run),
        "branch": run_head_branch(run),
        "status": f"{status}/{conclusion}",
        "reason": reason,
    }


def log_run_action(row: ActionRow, verbosity: str) -> None:
    """Log one workflow run action if permitted by verbosity."""
    action = row["action"]

    if not should_log_action(verbosity, action):
        return

    log(
        f"{action_emoji(action)} [{action}] {row['id']} | {row['created']} | "
        f"{row['workflow']} | {EMOJI_BRANCH} {row['branch']} | "
        f"{row['status']} | {row['reason']}"
    )


def maybe_delete_run(
    repo: str,
    token: str,
    run: Run,
    action: str,
    dry_run: bool,
    delete_sleep_seconds: float,
) -> None:
    """Delete a workflow run when selected and not in dry-run mode."""
    if action != "DELETE" or dry_run:
        return

    run_id = run_id_as_int(run)
    if run_id is None:
        error(f"Cannot delete workflow run with invalid id: {run.get('id')!r}")

    delete_workflow_run(repo, run_id, token)

    if delete_sleep_seconds:
        time.sleep(delete_sleep_seconds)


def log_progress(
    inspected_runs: int,
    total_runs: int,
    run_delete_count: int,
    run_keep_count: int,
    progress_every: int,
) -> None:
    """Log periodic workflow-run cleanup progress."""
    if not progress_every or inspected_runs % progress_every != 0:
        return

    log(
        f"{EMOJI_SUMMARY} [PROGRESS] inspected runs {inspected_runs}/{total_runs}, "
        f"{EMOJI_DELETE} deleted {run_delete_count}, "
        f"{EMOJI_KEEP} kept/skipped {run_keep_count}"
    )


def decide_run_action(
    run: Run,
    config: Config,
    cutoff: datetime,
    current_run_id: str,
    keep_run_ids: Set[int],
    run_delete_count: int,
) -> Tuple[str, str, bool]:
    """Return the action, reason and delete-cap state for one workflow run."""
    should_delete, reason = should_delete_run(
        run,
        cutoff=cutoff,
        current_run_id=current_run_id,
        keep_run_ids=keep_run_ids,
        preserve_branch=str(config_value(config, "Preserve branch")),
        force_delete_non_default_branch=bool(config_value(config, "Force delete non-default branch")),
        delete_skipped=bool(config_value(config, "Delete skipped")),
        delete_neutral=bool(config_value(config, "Delete neutral")),
    )

    if not should_delete:
        return "KEEP", reason, False

    max_deletes_per_run = int(config_value(config, "Max deletes per run"))
    if max_deletes_per_run and run_delete_count >= max_deletes_per_run:
        return "KEEP", "delete cap reached", True

    return "DELETE", reason, False


def process_workflow_runs(
    repo: str,
    token: str,
    current_run_id: str,
    config: Config,
) -> Tuple[List[ActionRow], WorkflowTotals, Dict[str, Any], Set[int]]:
    """Process workflow runs and perform selected deletions."""
    runs = fetch_all_workflow_runs(repo, token)
    total_runs = len(runs)
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(config_value(config, "Retention days")))

    keep_run_ids = find_keep_run_ids(
        runs,
        preserve_branch=str(config_value(config, "Preserve branch")),
        keep_latest_successful=bool(config_value(config, "Keep latest successful")),
        keep_latest_failed=bool(config_value(config, "Keep latest failed")),
        keep_latest_cancelled=bool(config_value(config, "Keep latest cancelled")),
        keep_latest_timed_out=bool(config_value(config, "Keep latest timed out")),
        keep_last_n_successful=int(config_value(config, "Keep last N successful")),
    )

    run_actions: List[ActionRow] = []
    workflow_totals: WorkflowTotals = {}
    inspected_runs = 0
    run_delete_count = 0
    run_keep_count = 0
    run_delete_cap_reached = False

    for run in sorted(runs, key=run_created_at):
        inspected_runs += 1
        log_progress(
            inspected_runs,
            total_runs,
            run_delete_count,
            run_keep_count,
            int(config_value(config, "Progress every")),
        )

        action, reason, cap_reached = decide_run_action(
            run,
            config,
            cutoff,
            current_run_id,
            keep_run_ids,
            run_delete_count,
        )

        run_delete_cap_reached = run_delete_cap_reached or cap_reached

        if action == "DELETE":
            run_delete_count += 1
        else:
            run_keep_count += 1

        workflow = workflow_display(run)
        increment_workflow_total(workflow_totals, workflow, action)

        row = build_run_action_row(run, action, reason)
        log_run_action(row, str(config_value(config, "Verbosity")))
        run_actions.append(row)

        maybe_delete_run(
            repo,
            token,
            run,
            action,
            dry_run_enabled(config),
            float(config_value(config, "Delete sleep seconds")),
        )

    stats = {
        "total_runs": total_runs,
        "inspected_runs": inspected_runs,
        "run_delete_count": run_delete_count,
        "run_keep_count": run_keep_count,
        "run_delete_cap_reached": run_delete_cap_reached,
    }

    return run_actions, workflow_totals, stats, keep_run_ids


def build_artifact_action_row(artifact: Artifact, action: str, reason: str) -> ActionRow:
    """Build one artifact action row for the report."""
    return {
        "action": action,
        "id": str(artifact.get("id")),
        "created": str(artifact.get("created_at") or ""),
        "name": str(artifact.get("name") or "unknown"),
        "size": str(artifact.get("size_in_bytes") or "0"),
        "reason": reason,
    }


def log_artifact_action(row: ActionRow, verbosity: str) -> None:
    """Log one artifact action if permitted by verbosity."""
    action = row["action"]

    if not should_log_action(verbosity, action):
        return

    log(
        f"{EMOJI_ARTIFACT} {action_emoji(action)} [{action}] "
        f"{row['id']} | {row['created']} | {row['name']} | {row['reason']}"
    )


def maybe_delete_artifact(
    repo: str,
    token: str,
    artifact: Artifact,
    action: str,
    dry_run: bool,
    delete_sleep_seconds: float,
) -> None:
    """Delete an artifact when selected and not in dry-run mode."""
    if action != "DELETE" or dry_run:
        return

    artifact_id = artifact_id_as_int(artifact)
    if artifact_id is None:
        error(f"Cannot delete artifact with invalid id: {artifact.get('id')!r}")

    delete_artifact(repo, artifact_id, token)

    if delete_sleep_seconds:
        time.sleep(delete_sleep_seconds)


def decide_artifact_action(
    artifact: Artifact,
    artifact_cutoff: datetime,
    artifact_delete_count: int,
    max_artifact_deletes_per_run: int,
) -> Tuple[str, str, bool]:
    """Return the action, reason and delete-cap state for one artifact."""
    should_delete, reason = should_delete_artifact(
        artifact,
        artifact_cutoff=artifact_cutoff,
    )

    if not should_delete:
        return "KEEP", reason, False

    if max_artifact_deletes_per_run and artifact_delete_count >= max_artifact_deletes_per_run:
        return "KEEP", "artifact delete cap reached", True

    return "DELETE", reason, False


def process_artifacts(
    repo: str,
    token: str,
    config: Config,
) -> Tuple[List[ActionRow], Dict[str, Any]]:
    """Process artifacts and perform selected deletions when enabled."""
    if not bool(config_value(config, "Cleanup artifacts")):
        return [], {
            "total_artifacts": 0,
            "artifact_delete_count": 0,
            "artifact_keep_count": 0,
            "artifact_delete_cap_reached": False,
        }

    artifacts = fetch_all_artifacts(repo, token)
    artifact_cutoff = datetime.now(timezone.utc) - timedelta(
        days=int(config_value(config, "Artifact retention days"))
    )

    artifact_actions: List[ActionRow] = []
    artifact_delete_count = 0
    artifact_keep_count = 0
    artifact_delete_cap_reached = False

    for artifact in sorted(artifacts, key=artifact_created_at):
        action, reason, cap_reached = decide_artifact_action(
            artifact,
            artifact_cutoff,
            artifact_delete_count,
            int(config_value(config, "Max artifact deletes per run")),
        )

        artifact_delete_cap_reached = artifact_delete_cap_reached or cap_reached

        if action == "DELETE":
            artifact_delete_count += 1
        else:
            artifact_keep_count += 1

        row = build_artifact_action_row(artifact, action, reason)
        log_artifact_action(row, str(config_value(config, "Verbosity")))
        artifact_actions.append(row)

        maybe_delete_artifact(
            repo,
            token,
            artifact,
            action,
            dry_run_enabled(config),
            float(config_value(config, "Delete sleep seconds")),
        )

    stats = {
        "total_artifacts": len(artifacts),
        "artifact_delete_count": artifact_delete_count,
        "artifact_keep_count": artifact_keep_count,
        "artifact_delete_cap_reached": artifact_delete_cap_reached,
    }

    return artifact_actions, stats


def build_summary(
    repo: str,
    config: Config,
    run_stats: Dict[str, Any],
    artifact_stats: Dict[str, Any],
    keep_run_ids: Set[int],
) -> Dict[str, Any]:
    """Build the final cleanup summary."""
    return {
        "Repository": repo,
        f"{EMOJI_CLEANUP} Mode": config_value(config, "Mode"),
        f"{EMOJI_RUN} Workflow runs fetched": run_stats["total_runs"],
        f"{EMOJI_RUN} Workflow runs inspected": run_stats["inspected_runs"],
        f"{EMOJI_DELETE} Workflow runs selected for deletion": run_stats["run_delete_count"],
        f"{EMOJI_KEEP} Workflow runs kept/skipped": run_stats["run_keep_count"],
        f"{EMOJI_KEEP} Preserved representative runs": len(keep_run_ids),
        f"{EMOJI_WARNING} Workflow run delete cap reached": run_stats["run_delete_cap_reached"],
        f"{EMOJI_ARTIFACT} Artifacts fetched": artifact_stats["total_artifacts"],
        f"{EMOJI_DELETE} Artifacts selected for deletion": artifact_stats["artifact_delete_count"],
        f"{EMOJI_KEEP} Artifacts kept/skipped": artifact_stats["artifact_keep_count"],
        f"{EMOJI_WARNING} Artifact delete cap reached": artifact_stats["artifact_delete_cap_reached"],
    }


def print_summary(summary: Dict[str, Any]) -> None:
    """Print the final cleanup summary to stdout."""
    log()
    log(f"{EMOJI_SUMMARY} Workflow run cleanup summary")
    log("============================")

    for key, value in summary.items():
        log(f"{key}: {value}")


def main() -> None:
    """Run workflow run and artifact cleanup."""
    repo, token, current_run_id = required_runtime_context()
    config = read_config_from_env()

    if config_value(config, "Verbosity") != "quiet":
        print_config(config)

    run_actions, workflow_totals, run_stats, keep_run_ids = process_workflow_runs(
        repo,
        token,
        current_run_id,
        config,
    )

    artifact_actions, artifact_stats = process_artifacts(repo, token, config)

    summary = build_summary(
        repo,
        config,
        run_stats,
        artifact_stats,
        keep_run_ids,
    )

    write_markdown_report(
        repo=repo,
        config=config,
        run_actions=run_actions,
        artifact_actions=artifact_actions,
        workflow_totals=workflow_totals,
        summary=summary,
    )

    print_summary(summary)
    log(f"{EMOJI_SUCCESS} Cleanup report generated")


if __name__ == "__main__":
    main()
