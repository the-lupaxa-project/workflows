#!/usr/bin/env python3
"""
Clean up old GitHub Actions workflow runs and optionally old artifacts.

This script is designed to run inside GitHub Actions.

It performs routine repository maintenance only:

- deletes completed workflow runs older than a retention period;
- optionally deletes completed runs whose workflow file no longer exists;
- preserves the latest N successful runs per workflow on a configured branch;
- optionally deletes old workflow artifacts;
- respects delete limits, retry settings, dry-run mode and progress output;
- writes a Markdown report.

Configuration is provided through environment variables.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, NoReturn
from urllib.error import HTTPError, URLError


API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_PER_PAGE = 100

DEFAULT_RETENTION_DAYS = 90
DEFAULT_ARTIFACT_RETENTION_DAYS = 90
DEFAULT_MAX_DELETES_PER_RUN = 250
DEFAULT_MAX_ARTIFACT_DELETES_PER_RUN = 250
DEFAULT_DELETE_SLEEP_SECONDS = 1.0
DEFAULT_PROGRESS_EVERY = 50
DEFAULT_PRESERVE_BRANCH = "master"
DEFAULT_VERBOSITY = "normal"
DEFAULT_API_RETRIES = 3

VALID_VERBOSITY = {"quiet", "normal", "verbose"}
RETRY_STATUS_CODES = {403, 429, 500, 502, 503, 504}

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
EMOJI_RETRY = "🔁"


Run = dict[str, Any]
Artifact = dict[str, Any]
ActionRow = dict[str, str]
WorkflowTotals = dict[str, dict[str, int]]


@dataclass
class Config:
    retention_days: int
    artifact_retention_days: int
    dry_run: bool
    cleanup_artifacts: bool
    remove_obsolete: bool
    preserve_branch: str
    keep_last_n_successful: int
    delete_skipped: bool
    delete_neutral: bool
    max_deletes_per_run: int
    max_artifact_deletes_per_run: int
    delete_sleep_seconds: float
    progress_every: int
    verbosity: str
    api_retries: int


@dataclass
class ApiStats:
    retries: int = 0


def log(message: str = "") -> None:
    print(message, flush=True)


def fail(message: str, *, code: int = 1) -> NoReturn:
    print(f"{EMOJI_WARNING} ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def env_value(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def github_token_from_env() -> str:
    return (
        env_value("GITHUB_TOKEN")
        or env_value("GH_TOKEN")
        or env_value("ACTIONS_RUNTIME_TOKEN")
    )


def parse_bool(value: str, *, default: bool) -> bool:
    if value == "":
        return default

    normalised = value.strip().lower()

    if normalised in {"1", "true", "yes", "y", "on"}:
        return True

    if normalised in {"0", "false", "no", "n", "off"}:
        return False

    return default


def parse_int(value: str, *, default: int) -> int:
    if value == "":
        return default

    try:
        return int(value)
    except ValueError:
        return default


def parse_float(value: str, *, default: float) -> float:
    if value == "":
        return default

    try:
        return float(value)
    except ValueError:
        return default


def parse_iso8601(value: str) -> datetime | None:
    value = value.strip()

    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_next_link(link_header: str) -> str | None:
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
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-._")

    return value or fallback


def md_value(value: Any) -> str:
    text = str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    return text.strip()


def action_emoji(action: str) -> str:
    if action == "DELETE":
        return EMOJI_DELETE

    if action == "KEEP":
        return EMOJI_KEEP

    return EMOJI_SKIP


def github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-workflow-clean-up",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def decode_http_error(exc: HTTPError) -> str:
    return exc.read().decode("utf-8", errors="replace")


def retry_delay(attempt: int) -> int:
    return min(60, 2**attempt * 5)


def github_request(
    url: str,
    token: str,
    api_stats: ApiStats,
    *,
    method: str = "GET",
    retries: int = DEFAULT_API_RETRIES,
) -> tuple[dict[str, Any] | None, str | None, int]:
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            headers=github_headers(token),
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.getcode()
                body = response.read()
                next_url = parse_next_link(response.headers.get("Link", ""))

                if method == "DELETE":
                    return None, None, status

                if not (200 <= status < 300):
                    fail(f"GitHub API returned HTTP {status} for {method} {url}")

                if not body:
                    return {}, next_url, status

                data = json.loads(body)

                if not isinstance(data, dict):
                    fail(f"GitHub API response from {url} was not an object.")

                return data, next_url, status

        except HTTPError as exc:
            body_text = decode_http_error(exc)

            if exc.code in RETRY_STATUS_CODES and attempt < retries:
                api_stats.retries += 1
                sleep_for = retry_delay(attempt)
                print(
                    f"{EMOJI_RETRY} [RETRY] {method} {url} failed with HTTP {exc.code}; retrying in {sleep_for}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(sleep_for)
                continue

            if body_text:
                print(body_text, file=sys.stderr, flush=True)

            fail(f"GitHub API returned HTTP {exc.code} for {method} {url}: {exc.reason}")

        except URLError as exc:
            if attempt < retries:
                api_stats.retries += 1
                sleep_for = retry_delay(attempt)
                print(
                    f"{EMOJI_RETRY} [RETRY] {method} {url} failed: {exc.reason}; retrying in {sleep_for}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(sleep_for)
                continue

            fail(f"Failed to reach GitHub API at {url}: {exc.reason}")

        except json.JSONDecodeError as exc:
            fail(f"Failed to decode JSON from {url}: {exc}")

    fail(f"{method} {url} failed after retries")


def fetch_paginated_items(
    url: str,
    token: str,
    api_stats: ApiStats,
    *,
    collection_key: str,
    emoji: str,
    label: str,
    retries: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = url

    while next_url:
        data, next_url, _status = github_request(
            next_url,
            token,
            api_stats,
            retries=retries,
        )

        if data is None:
            break

        page_items = data.get(collection_key, [])

        if isinstance(page_items, list):
            items.extend(item for item in page_items if isinstance(item, dict))

        log(f"{emoji} [FETCH] Loaded {len(items)} {label} so far")

    return items


def fetch_all_workflow_runs(repo: str, token: str, api_stats: ApiStats, config: Config) -> list[Run]:
    url = f"{API_BASE}/repos/{repo}/actions/runs?per_page={DEFAULT_PER_PAGE}"

    return fetch_paginated_items(
        url,
        token,
        api_stats,
        collection_key="workflow_runs",
        emoji=EMOJI_RUN,
        label="workflow runs",
        retries=config.api_retries,
    )


def fetch_all_artifacts(repo: str, token: str, api_stats: ApiStats, config: Config) -> list[Artifact]:
    url = f"{API_BASE}/repos/{repo}/actions/artifacts?per_page={DEFAULT_PER_PAGE}"

    return fetch_paginated_items(
        url,
        token,
        api_stats,
        collection_key="artifacts",
        emoji=EMOJI_ARTIFACT,
        label="artifacts",
        retries=config.api_retries,
    )


def fetch_all_workflows(repo: str, token: str, api_stats: ApiStats, config: Config) -> list[dict[str, Any]]:
    url = f"{API_BASE}/repos/{repo}/actions/workflows?per_page={DEFAULT_PER_PAGE}"

    return fetch_paginated_items(
        url,
        token,
        api_stats,
        collection_key="workflows",
        emoji=EMOJI_RUN,
        label="workflow definitions",
        retries=config.api_retries,
    )


def normalise_workflow_path(path: str) -> str:
    path = path.strip().replace("\\", "/")
    path = path.lstrip("./")

    return path.casefold()


def active_workflow_paths(repo: str, token: str, api_stats: ApiStats, config: Config) -> set[str]:
    paths: set[str] = set()

    for workflow in fetch_all_workflows(repo, token, api_stats, config):
        path = str(workflow.get("path") or "").strip()
        if path:
            paths.add(normalise_workflow_path(path))

    return paths


def run_workflow_path(run: Run) -> str:
    return str(run.get("path") or "").strip()


def is_obsolete_workflow_run(run: Run, current_workflow_paths: set[str]) -> bool:
    path = run_workflow_path(run)

    if not path:
        return False

    return normalise_workflow_path(path) not in current_workflow_paths


def workflow_key(run: Run) -> str:
    workflow_id = run.get("workflow_id")

    if workflow_id is not None:
        return str(workflow_id)

    path = str(run.get("path") or "")
    if path:
        return path

    return str(run.get("name") or "unknown")


def workflow_display(run: Run) -> str:
    name = str(run.get("name") or "unknown")
    path = str(run.get("path") or "")

    if path:
        return f"{name} ({path})"

    return name


def run_created_at(run: Run) -> datetime:
    created_at = parse_iso8601(str(run.get("created_at") or ""))

    if created_at:
        return created_at

    return datetime.fromtimestamp(0, timezone.utc)


def artifact_created_at(artifact: Artifact) -> datetime:
    created_at = parse_iso8601(str(artifact.get("created_at") or ""))

    if created_at:
        return created_at

    return datetime.fromtimestamp(0, timezone.utc)


def run_id_as_int(run: Run) -> int | None:
    run_id = run.get("id")

    if isinstance(run_id, int):
        return run_id

    return None


def artifact_id_as_int(artifact: Artifact) -> int | None:
    artifact_id = artifact.get("id")

    if isinstance(artifact_id, int):
        return artifact_id

    return None


def run_status(run: Run) -> str:
    return str(run.get("status") or "").strip().lower()


def run_conclusion(run: Run) -> str:
    return str(run.get("conclusion") or "").strip().lower()


def run_head_branch(run: Run) -> str:
    return str(run.get("head_branch") or "").strip()


def group_preserved_branch_runs(runs: list[Run], preserve_branch: str) -> dict[str, list[Run]]:
    grouped: dict[str, list[Run]] = {}

    for run in runs:
        if run_status(run) != "completed":
            continue

        if run_head_branch(run) != preserve_branch:
            continue

        grouped.setdefault(workflow_key(run), []).append(run)

    return grouped


def find_keep_run_ids(
    runs: list[Run],
    *,
    preserve_branch: str,
    keep_last_n_successful: int,
) -> set[int]:
    keep_ids: set[int] = set()
    grouped = group_preserved_branch_runs(runs, preserve_branch)

    for workflow_runs in grouped.values():
        successful_runs = [
            run
            for run in sorted(workflow_runs, key=run_created_at, reverse=True)
            if run_conclusion(run) == "success"
        ]

        for run in successful_runs[:keep_last_n_successful]:
            run_id = run_id_as_int(run)
            if run_id is not None:
                keep_ids.add(run_id)

    return keep_ids


def should_delete_run(
    run: Run,
    *,
    cutoff: datetime,
    current_run_id: str,
    keep_run_ids: set[int],
    current_workflow_paths: set[str],
    config: Config,
) -> tuple[bool, str]:
    run_id = run.get("id")
    status = run_status(run)
    conclusion = run_conclusion(run)

    if str(run_id) == current_run_id:
        return False, "current cleanup run"

    if status != "completed":
        return False, f"not completed: {status}"

    if config.remove_obsolete and is_obsolete_workflow_run(run, current_workflow_paths):
        return True, f"obsolete workflow file: {run_workflow_path(run)}"

    if isinstance(run_id, int) and run_id in keep_run_ids:
        return False, "preserved successful representative run"

    if conclusion == "skipped" and not config.delete_skipped:
        return False, "skipped deletion disabled"

    if conclusion == "neutral" and not config.delete_neutral:
        return False, "neutral deletion disabled"

    if run_created_at(run) >= cutoff:
        return False, "newer than cutoff"

    return True, "old completed run"


def should_delete_artifact(
    artifact: Artifact,
    *,
    artifact_cutoff: datetime,
) -> tuple[bool, str]:
    expired = artifact.get("expired")

    if expired is True:
        return True, "artifact already expired"

    if artifact_created_at(artifact) >= artifact_cutoff:
        return False, "artifact newer than cutoff"

    return True, "old artifact"


def delete_workflow_run(repo: str, run_id: int, token: str, api_stats: ApiStats, config: Config) -> None:
    url = f"{API_BASE}/repos/{repo}/actions/runs/{run_id}"
    _data, _next_url, status = github_request(
        url,
        token,
        api_stats,
        method="DELETE",
        retries=config.api_retries,
    )

    if status not in {202, 204}:
        fail(f"Unexpected HTTP {status} deleting workflow run {run_id}")


def delete_artifact(repo: str, artifact_id: int, token: str, api_stats: ApiStats, config: Config) -> None:
    url = f"{API_BASE}/repos/{repo}/actions/artifacts/{artifact_id}"
    _data, _next_url, status = github_request(
        url,
        token,
        api_stats,
        method="DELETE",
        retries=config.api_retries,
    )

    if status not in {202, 204}:
        fail(f"Unexpected HTTP {status} deleting artifact {artifact_id}")


def default_report_filename(repo: str) -> str:
    run_id = env_value("GITHUB_RUN_ID", "unknown")
    run_attempt = env_value("GITHUB_RUN_ATTEMPT", "1")
    repo_slug = slugify(repo.replace("/", "-"))
    output_dir = env_value("RUNNER_TEMP").strip() or os.getcwd()

    filename = f"cleanup-workflow-runs-{repo_slug}-{run_id}-attempt-{run_attempt}.md"

    return str(Path(output_dir) / filename)


def report_paths(repo: str) -> list[Path]:
    paths: list[Path] = []

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
    step_summary = env_value("GITHUB_STEP_SUMMARY").strip()

    return "a" if str(path) == step_summary else "w"


def write_table_rows(rows: dict[str, Any], out: Any) -> None:
    for key, value in rows.items():
        print(f"| {md_value(key)} | {md_value(value)} |", file=out)


def write_summary_section(summary: dict[str, Any], out: Any) -> None:
    print(f"## {EMOJI_SUMMARY} Summary", file=out)
    print(file=out)
    print("| Field | Value |", file=out)
    print("| :---- | :---- |", file=out)
    write_table_rows(summary, out)
    print(file=out)


def write_config_section(config: Config, out: Any) -> None:
    print(f"## {EMOJI_STAR} Configuration", file=out)
    print(file=out)
    print("| Field | Value |", file=out)
    print("| :---- | :---- |", file=out)
    write_table_rows(config_to_report(config), out)
    print(file=out)


def write_workflow_totals_section(workflow_totals: WorkflowTotals, out: Any) -> None:
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


def write_run_actions_section(run_actions: list[ActionRow], out: Any) -> None:
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


def write_artifact_actions_section(artifact_actions: list[ActionRow], out: Any) -> None:
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
    run_actions: list[ActionRow],
    artifact_actions: list[ActionRow],
    workflow_totals: WorkflowTotals,
    summary: dict[str, Any],
) -> None:
    with path.open(report_mode(path), encoding="utf-8") as out:
        print(f"# {EMOJI_CLEANUP} Workflow Clean Up Report", file=out)
        print(file=out)
        write_summary_section(summary, out)
        write_config_section(config, out)
        write_workflow_totals_section(workflow_totals, out)
        write_run_actions_section(run_actions, out)
        write_artifact_actions_section(artifact_actions, out)


def write_markdown_report(
    repo: str,
    config: Config,
    run_actions: list[ActionRow],
    artifact_actions: list[ActionRow],
    workflow_totals: WorkflowTotals,
    summary: dict[str, Any],
) -> None:
    for path in report_paths(repo):
        write_report_file(
            path=path,
            config=config,
            run_actions=run_actions,
            artifact_actions=artifact_actions,
            workflow_totals=workflow_totals,
            summary=summary,
        )


def should_log_action(verbosity: str, action: str) -> bool:
    if verbosity == "quiet":
        return False

    if verbosity == "normal":
        return action == "DELETE"

    return True


def log_run_action(row: ActionRow, verbosity: str) -> None:
    action = row["action"]

    if not should_log_action(verbosity, action):
        return

    log(
        f"{action_emoji(action)} [{action}] {row['id']} | {row['created']} | "
        f"{row['workflow']} | {EMOJI_BRANCH} {row['branch']} | "
        f"{row['status']} | {row['reason']}"
    )


def log_artifact_action(row: ActionRow, verbosity: str) -> None:
    action = row["action"]

    if not should_log_action(verbosity, action):
        return

    log(
        f"{EMOJI_ARTIFACT} {action_emoji(action)} [{action}] "
        f"{row['id']} | {row['created']} | {row['name']} | {row['reason']}"
    )


def required_runtime_context() -> tuple[str, str, str]:
    repo = env_value("GITHUB_REPOSITORY").strip()
    token = github_token_from_env()
    current_run_id = env_value("GITHUB_RUN_ID").strip()

    if not repo:
        fail("GITHUB_REPOSITORY is required.")

    if not token:
        fail("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is required.")

    return repo, token, current_run_id


def validate_minimum(name: str, value: int, minimum: int) -> None:
    if value < minimum:
        fail(f"{name} must be at least {minimum}.")


def validate_non_negative(name: str, value: int) -> None:
    if value < 0:
        fail(f"{name} must be 0 or greater.")


def validate_float_non_negative(name: str, value: float) -> None:
    if value < 0:
        fail(f"{name} must be 0 or greater.")


def parse_verbosity() -> str:
    verbosity = env_value("CLEANUP_WORKFLOW_RUNS_VERBOSITY", DEFAULT_VERBOSITY).strip().lower()

    if verbosity not in VALID_VERBOSITY:
        return DEFAULT_VERBOSITY

    return verbosity


def read_config_from_env() -> Config:
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

    api_retries = parse_int(
        env_value("CLEANUP_WORKFLOW_RUNS_API_RETRIES"),
        default=DEFAULT_API_RETRIES,
    )
    validate_non_negative("CLEANUP_WORKFLOW_RUNS_API_RETRIES", api_retries)

    preserve_branch = env_value(
        "CLEANUP_WORKFLOW_RUNS_PRESERVE_BRANCH",
        DEFAULT_PRESERVE_BRANCH,
    ).strip() or DEFAULT_PRESERVE_BRANCH

    return Config(
        retention_days=retention_days,
        artifact_retention_days=artifact_retention_days,
        dry_run=parse_bool(env_value("CLEANUP_WORKFLOW_RUNS_DRY_RUN"), default=True),
        cleanup_artifacts=parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_CLEANUP_ARTIFACTS"),
            default=True,
        ),
        remove_obsolete=parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_REMOVE_OBSOLETE"),
            default=True,
        ),
        preserve_branch=preserve_branch,
        keep_last_n_successful=keep_last_n_successful,
        delete_skipped=parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_DELETE_SKIPPED"),
            default=True,
        ),
        delete_neutral=parse_bool(
            env_value("CLEANUP_WORKFLOW_RUNS_DELETE_NEUTRAL"),
            default=True,
        ),
        max_deletes_per_run=max_deletes_per_run,
        max_artifact_deletes_per_run=max_artifact_deletes_per_run,
        delete_sleep_seconds=delete_sleep_seconds,
        progress_every=progress_every,
        verbosity=parse_verbosity(),
        api_retries=api_retries,
    )


def config_to_report(config: Config) -> dict[str, Any]:
    return {
        f"{EMOJI_CLEANUP} Mode": "DRY RUN" if config.dry_run else "DELETE",
        f"{EMOJI_RUN} Retention days": config.retention_days,
        f"{EMOJI_ARTIFACT} Artifact retention days": config.artifact_retention_days,
        f"{EMOJI_ARTIFACT} Cleanup artifacts": config.cleanup_artifacts,
        f"{EMOJI_DELETE} Remove obsolete": config.remove_obsolete,
        f"{EMOJI_BRANCH} Preserve branch": config.preserve_branch,
        f"{EMOJI_KEEP} Keep last N successful": config.keep_last_n_successful,
        f"{EMOJI_DELETE} Delete skipped": config.delete_skipped,
        f"{EMOJI_DELETE} Delete neutral": config.delete_neutral,
        f"{EMOJI_DELETE} Max deletes per run": config.max_deletes_per_run,
        f"{EMOJI_ARTIFACT} Max artifact deletes per run": config.max_artifact_deletes_per_run,
        f"{EMOJI_SLEEP} Delete sleep seconds": config.delete_sleep_seconds,
        f"{EMOJI_SUMMARY} Progress every": config.progress_every,
        f"{EMOJI_VERBOSITY} Verbosity": config.verbosity,
        f"{EMOJI_RETRY} API retries": config.api_retries,
    }


def print_config(config: Config) -> None:
    log(f"{EMOJI_CLEANUP} Workflow clean up configuration")
    log("===================================")

    for key, value in config_to_report(config).items():
        log(f"{key}: {value}")

    log()


def dry_run_mode(config: Config) -> bool:
    return config.dry_run


def increment_workflow_total(workflow_totals: WorkflowTotals, workflow: str, action: str) -> None:
    workflow_totals.setdefault(workflow, {"deleted": 0, "kept": 0})

    if action == "DELETE":
        workflow_totals[workflow]["deleted"] += 1
    else:
        workflow_totals[workflow]["kept"] += 1


def build_run_action_row(run: Run, action: str, reason: str) -> ActionRow:
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


def build_artifact_action_row(artifact: Artifact, action: str, reason: str) -> ActionRow:
    return {
        "action": action,
        "id": str(artifact.get("id")),
        "created": str(artifact.get("created_at") or ""),
        "name": str(artifact.get("name") or "unknown"),
        "size": str(artifact.get("size_in_bytes") or "0"),
        "reason": reason,
    }


def maybe_delete_run(
    repo: str,
    token: str,
    api_stats: ApiStats,
    config: Config,
    run: Run,
    action: str,
) -> None:
    if action != "DELETE" or dry_run_mode(config):
        return

    run_id = run_id_as_int(run)
    if run_id is None:
        fail(f"Cannot delete workflow run with invalid id: {run.get('id')!r}")

    delete_workflow_run(repo, run_id, token, api_stats, config)

    if config.delete_sleep_seconds:
        time.sleep(config.delete_sleep_seconds)


def maybe_delete_artifact(
    repo: str,
    token: str,
    api_stats: ApiStats,
    config: Config,
    artifact: Artifact,
    action: str,
) -> None:
    if action != "DELETE" or dry_run_mode(config):
        return

    artifact_id = artifact_id_as_int(artifact)
    if artifact_id is None:
        fail(f"Cannot delete artifact with invalid id: {artifact.get('id')!r}")

    delete_artifact(repo, artifact_id, token, api_stats, config)

    if config.delete_sleep_seconds:
        time.sleep(config.delete_sleep_seconds)


def log_progress(
    inspected_runs: int,
    total_runs: int,
    run_delete_count: int,
    run_keep_count: int,
    progress_every: int,
) -> None:
    if not progress_every or inspected_runs % progress_every != 0:
        return

    log(
        f"{EMOJI_SUMMARY} [PROGRESS] inspected runs {inspected_runs}/{total_runs}, "
        f"{EMOJI_DELETE} selected {run_delete_count}, "
        f"{EMOJI_KEEP} kept/skipped {run_keep_count}"
    )


def decide_run_action(
    run: Run,
    *,
    config: Config,
    cutoff: datetime,
    current_run_id: str,
    keep_run_ids: set[int],
    current_workflow_paths: set[str],
    run_delete_count: int,
) -> tuple[str, str, bool]:
    should_delete, reason = should_delete_run(
        run,
        cutoff=cutoff,
        current_run_id=current_run_id,
        keep_run_ids=keep_run_ids,
        current_workflow_paths=current_workflow_paths,
        config=config,
    )

    if not should_delete:
        return "KEEP", reason, False

    if config.max_deletes_per_run and run_delete_count >= config.max_deletes_per_run:
        return "KEEP", "delete cap reached", True

    return "DELETE", reason, False


def process_workflow_runs(
    repo: str,
    token: str,
    current_run_id: str,
    config: Config,
    api_stats: ApiStats,
) -> tuple[list[ActionRow], WorkflowTotals, dict[str, Any], set[int]]:
    runs = fetch_all_workflow_runs(repo, token, api_stats, config)
    total_runs = len(runs)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=config.retention_days)
    current_workflow_paths: set[str] = set()

    if config.remove_obsolete:
        current_workflow_paths = active_workflow_paths(repo, token, api_stats, config)

    keep_run_ids = find_keep_run_ids(
        runs,
        preserve_branch=config.preserve_branch,
        keep_last_n_successful=config.keep_last_n_successful,
    )

    run_actions: list[ActionRow] = []
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
            config.progress_every,
        )

        action, reason, cap_reached = decide_run_action(
            run,
            config=config,
            cutoff=cutoff,
            current_run_id=current_run_id,
            keep_run_ids=keep_run_ids,
            current_workflow_paths=current_workflow_paths,
            run_delete_count=run_delete_count,
        )

        run_delete_cap_reached = run_delete_cap_reached or cap_reached

        if action == "DELETE":
            run_delete_count += 1
        else:
            run_keep_count += 1

        workflow = workflow_display(run)
        increment_workflow_total(workflow_totals, workflow, action)

        row = build_run_action_row(run, action, reason)
        log_run_action(row, config.verbosity)
        run_actions.append(row)

        maybe_delete_run(
            repo,
            token,
            api_stats,
            config,
            run,
            action,
        )

    stats = {
        "total_runs": total_runs,
        "inspected_runs": inspected_runs,
        "run_delete_count": run_delete_count,
        "run_keep_count": run_keep_count,
        "run_delete_cap_reached": run_delete_cap_reached,
        "current_workflow_paths": len(current_workflow_paths),
    }

    return run_actions, workflow_totals, stats, keep_run_ids


def decide_artifact_action(
    artifact: Artifact,
    artifact_cutoff: datetime,
    artifact_delete_count: int,
    max_artifact_deletes_per_run: int,
) -> tuple[str, str, bool]:
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
    api_stats: ApiStats,
) -> tuple[list[ActionRow], dict[str, Any]]:
    if not config.cleanup_artifacts:
        return [], {
            "total_artifacts": 0,
            "artifact_delete_count": 0,
            "artifact_keep_count": 0,
            "artifact_delete_cap_reached": False,
        }

    artifacts = fetch_all_artifacts(repo, token, api_stats, config)
    artifact_cutoff = datetime.now(timezone.utc) - timedelta(days=config.artifact_retention_days)

    artifact_actions: list[ActionRow] = []
    artifact_delete_count = 0
    artifact_keep_count = 0
    artifact_delete_cap_reached = False

    for artifact in sorted(artifacts, key=artifact_created_at):
        action, reason, cap_reached = decide_artifact_action(
            artifact,
            artifact_cutoff,
            artifact_delete_count,
            config.max_artifact_deletes_per_run,
        )

        artifact_delete_cap_reached = artifact_delete_cap_reached or cap_reached

        if action == "DELETE":
            artifact_delete_count += 1
        else:
            artifact_keep_count += 1

        row = build_artifact_action_row(artifact, action, reason)
        log_artifact_action(row, config.verbosity)
        artifact_actions.append(row)

        maybe_delete_artifact(
            repo,
            token,
            api_stats,
            config,
            artifact,
            action,
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
    run_stats: dict[str, Any],
    artifact_stats: dict[str, Any],
    keep_run_ids: set[int],
    api_stats: ApiStats,
) -> dict[str, Any]:
    return {
        "Repository": repo,
        f"{EMOJI_CLEANUP} Mode": "DRY RUN" if config.dry_run else "DELETE",
        f"{EMOJI_RUN} Workflow runs fetched": run_stats["total_runs"],
        f"{EMOJI_RUN} Workflow runs inspected": run_stats["inspected_runs"],
        f"{EMOJI_DELETE} Workflow runs selected for deletion": run_stats["run_delete_count"],
        f"{EMOJI_KEEP} Workflow runs kept/skipped": run_stats["run_keep_count"],
        f"{EMOJI_KEEP} Preserved successful representative runs": len(keep_run_ids),
        f"{EMOJI_WARNING} Workflow run delete cap reached": run_stats["run_delete_cap_reached"],
        f"{EMOJI_RUN} Current workflow definitions": run_stats["current_workflow_paths"],
        f"{EMOJI_ARTIFACT} Artifacts fetched": artifact_stats["total_artifacts"],
        f"{EMOJI_DELETE} Artifacts selected for deletion": artifact_stats["artifact_delete_count"],
        f"{EMOJI_KEEP} Artifacts kept/skipped": artifact_stats["artifact_keep_count"],
        f"{EMOJI_WARNING} Artifact delete cap reached": artifact_stats["artifact_delete_cap_reached"],
        f"{EMOJI_RETRY} API retries": api_stats.retries,
    }


def print_summary(summary: dict[str, Any]) -> None:
    log()
    log(f"{EMOJI_SUMMARY} Workflow clean up summary")
    log("=========================")

    for key, value in summary.items():
        log(f"{key}: {value}")


def main() -> None:
    repo, token, current_run_id = required_runtime_context()
    config = read_config_from_env()
    api_stats = ApiStats()

    if config.verbosity != "quiet":
        print_config(config)

    run_actions, workflow_totals, run_stats, keep_run_ids = process_workflow_runs(
        repo,
        token,
        current_run_id,
        config,
        api_stats,
    )

    artifact_actions, artifact_stats = process_artifacts(
        repo,
        token,
        config,
        api_stats,
    )

    summary = build_summary(
        repo,
        config,
        run_stats,
        artifact_stats,
        keep_run_ids,
        api_stats,
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
