#!/usr/bin/env python3
"""
Cleanup old GitHub Actions workflow runs.

Deletes completed workflow runs older than the configured retention period,
while preserving selected representative runs per workflow.

Representative preservation defaults to the repository default branch only,
so old Dependabot/feature-branch runs are not kept just because they are the
only run for that branch.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple
from urllib.error import HTTPError, URLError


DEFAULT_RETENTION_DAYS = 90
DEFAULT_PER_PAGE = 100
DEFAULT_MAX_DELETES_PER_RUN = 250
DEFAULT_DELETE_SLEEP_SECONDS = 1.0
DEFAULT_PROGRESS_EVERY = 50


def log(message: str = "") -> None:
    print(message, flush=True)


def error(message: str, *, code: int = 1) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def parse_bool(value: str, *, default: bool) -> bool:
    if value == "":
        return default

    value = value.strip().lower()

    if value in ("1", "true", "yes", "y", "on"):
        return True

    if value in ("0", "false", "no", "n", "off"):
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


def parse_iso8601(value: str) -> Optional[datetime]:
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


def github_request(
    url: str,
    token: str,
    *,
    method: str = "GET",
) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-cleanup-workflow-runs",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body = resp.read()
            next_url = parse_next_link(resp.headers.get("Link", ""))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if body:
            print(body, file=sys.stderr, flush=True)
        error(f"GitHub API returned HTTP {exc.code} for {method} {url}: {exc.reason}")
    except URLError as exc:
        error(f"Failed to reach GitHub API at {url}: {exc.reason}")

    if method == "DELETE":
        return None, None, status

    if not (200 <= status < 300):
        error(f"GitHub API returned HTTP {status} for {method} {url}")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode JSON from {url}: {exc}")

    if not isinstance(data, dict):
        error(f"GitHub API response from {url} was not an object.")

    return data, next_url, status


def fetch_all_workflow_runs(repo: str, token: str) -> List[Dict[str, Any]]:
    url: Optional[str] = (
        f"https://api.github.com/repos/{repo}/actions/runs"
        f"?per_page={DEFAULT_PER_PAGE}"
    )

    runs: List[Dict[str, Any]] = []

    while url:
        data, next_url, _status = github_request(url, token)

        if data is None:
            break

        page_runs = data.get("workflow_runs", [])

        if isinstance(page_runs, list):
            for run in page_runs:
                if isinstance(run, dict):
                    runs.append(run)

        log(f"[FETCH] Loaded {len(runs)} workflow runs so far")
        url = next_url

    return runs


def workflow_key(run: Dict[str, Any]) -> str:
    workflow_id = run.get("workflow_id")
    if workflow_id is not None:
        return str(workflow_id)

    path = str(run.get("path") or "")
    if path:
        return path

    return str(run.get("name") or "unknown")


def run_created_at(run: Dict[str, Any]) -> datetime:
    created_at = parse_iso8601(str(run.get("created_at") or ""))
    if created_at:
        return created_at

    return datetime.fromtimestamp(0, timezone.utc)


def run_id_as_int(run: Dict[str, Any]) -> Optional[int]:
    run_id = run.get("id")
    if isinstance(run_id, int):
        return run_id

    return None


def run_status(run: Dict[str, Any]) -> str:
    return str(run.get("status") or "").strip().lower()


def run_conclusion(run: Dict[str, Any]) -> str:
    return str(run.get("conclusion") or "").strip().lower()


def run_head_branch(run: Dict[str, Any]) -> str:
    return str(run.get("head_branch") or "").strip()


def repository_default_branch_from_runs(runs: List[Dict[str, Any]]) -> str:
    for run in runs:
        repository = run.get("repository") or {}
        if not isinstance(repository, dict):
            continue

        default_branch = str(repository.get("default_branch") or "").strip()
        if default_branch:
            return default_branch

    return "main"


def keep_latest_by_conclusion(
    runs: List[Dict[str, Any]],
    conclusion: str,
    keep_ids: Set[int],
) -> None:
    for run in runs:
        if run_conclusion(run) != conclusion:
            continue

        run_id = run_id_as_int(run)
        if run_id is not None:
            keep_ids.add(run_id)

        return


def keep_last_n_by_conclusion(
    runs: List[Dict[str, Any]],
    conclusion: str,
    count: int,
    keep_ids: Set[int],
) -> None:
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


def filter_representative_candidates(
    runs: List[Dict[str, Any]],
    *,
    default_branch: str,
    default_branch_only: bool,
) -> List[Dict[str, Any]]:
    if not default_branch_only:
        return runs

    return [
        run
        for run in runs
        if run_head_branch(run) == default_branch
    ]


def find_keep_run_ids(
    runs: List[Dict[str, Any]],
    *,
    keep_latest_successful: bool,
    keep_latest_failed: bool,
    keep_latest_cancelled: bool,
    keep_latest_timed_out: bool,
    keep_last_n_successful: int,
    keep_representatives_default_branch_only: bool,
    default_branch: str,
) -> Set[int]:
    keep_ids: Set[int] = set()
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for run in runs:
        if run_status(run) != "completed":
            continue

        grouped.setdefault(workflow_key(run), []).append(run)

    for workflow_runs in grouped.values():
        candidate_runs = filter_representative_candidates(
            workflow_runs,
            default_branch=default_branch,
            default_branch_only=keep_representatives_default_branch_only,
        )

        completed_sorted = sorted(
            candidate_runs,
            key=run_created_at,
            reverse=True,
        )

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
    run: Dict[str, Any],
    *,
    cutoff: datetime,
    current_run_id: str,
    keep_run_ids: Set[int],
    delete_skipped: bool,
    delete_neutral: bool,
) -> Tuple[bool, str]:
    run_id = run.get("id")
    status = run_status(run)
    conclusion = run_conclusion(run)

    if str(run_id) == current_run_id:
        return False, "current cleanup run"

    if isinstance(run_id, int) and run_id in keep_run_ids:
        return False, "preserved representative run"

    if status != "completed":
        return False, f"not completed: {status}"

    if conclusion == "skipped" and not delete_skipped:
        return False, "skipped deletion disabled"

    if conclusion == "neutral" and not delete_neutral:
        return False, "neutral deletion disabled"

    if run_created_at(run) >= cutoff:
        return False, "newer than cutoff"

    return True, "old completed run"


def delete_workflow_run(repo: str, run_id: int, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    _data, _next_url, status = github_request(url, token, method="DELETE")

    if status not in (202, 204):
        error(f"Unexpected HTTP {status} deleting workflow run {run_id}")


def print_config(
    *,
    dry_run: bool,
    retention_days: int,
    keep_latest_successful: bool,
    keep_latest_failed: bool,
    keep_latest_cancelled: bool,
    keep_latest_timed_out: bool,
    keep_last_n_successful: int,
    delete_skipped: bool,
    delete_neutral: bool,
    max_deletes_per_run: int,
    delete_sleep_seconds: float,
    progress_every: int,
    keep_representatives_default_branch_only: bool,
    default_branch: str,
) -> None:
    log("Workflow run cleanup configuration")
    log("==================================")
    log(f"Mode: {'DRY RUN' if dry_run else 'DELETE'}")
    log(f"Retention days: {retention_days}")
    log(f"Default branch: {default_branch}")
    log(f"Keep representatives default branch only: {keep_representatives_default_branch_only}")
    log(f"Keep latest successful: {keep_latest_successful}")
    log(f"Keep latest failed: {keep_latest_failed}")
    log(f"Keep latest cancelled: {keep_latest_cancelled}")
    log(f"Keep latest timed out: {keep_latest_timed_out}")
    log(f"Keep last N successful: {keep_last_n_successful}")
    log(f"Delete skipped: {delete_skipped}")
    log(f"Delete neutral: {delete_neutral}")
    log(f"Max deletes per run: {max_deletes_per_run}")
    log(f"Delete sleep seconds: {delete_sleep_seconds}")
    log(f"Progress every: {progress_every}")
    log()


def print_summary(
    *,
    total: int,
    inspected: int,
    delete_count: int,
    keep_count: int,
    dry_run: bool,
    retention_days: int,
    preserved_count: int,
    delete_cap_reached: bool,
) -> None:
    log()
    log("Workflow run cleanup summary")
    log("============================")
    log(f"Mode: {'DRY RUN' if dry_run else 'DELETE'}")
    log(f"Retention days: {retention_days}")
    log(f"Workflow runs fetched: {total}")
    log(f"Workflow runs inspected: {inspected}")
    log(f"Preserved representative runs: {preserved_count}")
    log(f"Runs selected for deletion: {delete_count}")
    log(f"Runs kept/skipped: {keep_count}")
    log(f"Delete cap reached: {delete_cap_reached}")


def main() -> None:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    current_run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    token = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("ACTIONS_RUNTIME_TOKEN")
    )

    if not repo:
        error("GITHUB_REPOSITORY is required.")

    if not token:
        error("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is required.")

    retention_days = parse_int(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_RETENTION_DAYS", ""),
        default=DEFAULT_RETENTION_DAYS,
    )
    if retention_days < 14:
        error("CLEANUP_WORKFLOW_RUNS_RETENTION_DAYS must be at least 14.")

    dry_run = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_DRY_RUN", ""),
        default=True,
    )

    keep_latest_successful = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_SUCCESSFUL", ""),
        default=True,
    )

    keep_latest_failed = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_FAILED", ""),
        default=True,
    )

    keep_latest_cancelled = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_CANCELLED", ""),
        default=True,
    )

    keep_latest_timed_out = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_KEEP_LATEST_TIMED_OUT", ""),
        default=True,
    )

    keep_last_n_successful = parse_int(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_KEEP_LAST_N_SUCCESSFUL", ""),
        default=3,
    )
    if keep_last_n_successful < 0:
        error("CLEANUP_WORKFLOW_RUNS_KEEP_LAST_N_SUCCESSFUL must be 0 or greater.")

    delete_skipped = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_DELETE_SKIPPED", ""),
        default=True,
    )

    delete_neutral = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_DELETE_NEUTRAL", ""),
        default=True,
    )

    max_deletes_per_run = parse_int(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_MAX_DELETES", ""),
        default=DEFAULT_MAX_DELETES_PER_RUN,
    )
    if max_deletes_per_run < 0:
        error("CLEANUP_WORKFLOW_RUNS_MAX_DELETES must be 0 or greater.")

    delete_sleep_seconds = parse_float(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_DELETE_SLEEP_SECONDS", ""),
        default=DEFAULT_DELETE_SLEEP_SECONDS,
    )
    if delete_sleep_seconds < 0:
        error("CLEANUP_WORKFLOW_RUNS_DELETE_SLEEP_SECONDS must be 0 or greater.")

    progress_every = parse_int(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_PROGRESS_EVERY", ""),
        default=DEFAULT_PROGRESS_EVERY,
    )
    if progress_every < 0:
        error("CLEANUP_WORKFLOW_RUNS_PROGRESS_EVERY must be 0 or greater.")

    keep_representatives_default_branch_only = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_KEEP_REPRESENTATIVES_DEFAULT_BRANCH_ONLY", ""),
        default=True,
    )

    runs = fetch_all_workflow_runs(repo, token)
    default_branch = repository_default_branch_from_runs(runs)

    print_config(
        dry_run=dry_run,
        retention_days=retention_days,
        keep_latest_successful=keep_latest_successful,
        keep_latest_failed=keep_latest_failed,
        keep_latest_cancelled=keep_latest_cancelled,
        keep_latest_timed_out=keep_latest_timed_out,
        keep_last_n_successful=keep_last_n_successful,
        delete_skipped=delete_skipped,
        delete_neutral=delete_neutral,
        max_deletes_per_run=max_deletes_per_run,
        delete_sleep_seconds=delete_sleep_seconds,
        progress_every=progress_every,
        keep_representatives_default_branch_only=keep_representatives_default_branch_only,
        default_branch=default_branch,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    keep_run_ids = find_keep_run_ids(
        runs,
        keep_latest_successful=keep_latest_successful,
        keep_latest_failed=keep_latest_failed,
        keep_latest_cancelled=keep_latest_cancelled,
        keep_latest_timed_out=keep_latest_timed_out,
        keep_last_n_successful=keep_last_n_successful,
        keep_representatives_default_branch_only=keep_representatives_default_branch_only,
        default_branch=default_branch,
    )

    delete_count = 0
    keep_count = 0
    inspected = 0
    delete_cap_reached = False
    total_runs = len(runs)

    for run in sorted(runs, key=run_created_at):
        inspected += 1

        run_id = run.get("id")
        name = str(run.get("name") or "unknown")
        path = str(run.get("path") or "")
        branch = run_head_branch(run)
        status = run_status(run)
        conclusion = run_conclusion(run)
        created_at = str(run.get("created_at") or "")

        if progress_every and inspected % progress_every == 0:
            log(
                f"[PROGRESS] inspected {inspected}/{total_runs}, "
                f"deleted {delete_count}, kept/skipped {keep_count}"
            )

        should_delete, reason = should_delete_run(
            run,
            cutoff=cutoff,
            current_run_id=current_run_id,
            keep_run_ids=keep_run_ids,
            delete_skipped=delete_skipped,
            delete_neutral=delete_neutral,
        )

        if not should_delete:
            keep_count += 1
            log(
                f"[KEEP]   {run_id} | {created_at} | {name} | "
                f"{branch} | {status}/{conclusion} | {reason}"
            )
            continue

        if max_deletes_per_run and delete_count >= max_deletes_per_run:
            keep_count += 1
            delete_cap_reached = True
            log(
                f"[KEEP]   {run_id} | {created_at} | {name} | "
                f"{branch} | {status}/{conclusion} | delete cap reached"
            )
            continue

        delete_count += 1
        log(
            f"[DELETE] {run_id} | {created_at} | {name} | "
            f"{branch} | {status}/{conclusion} | {path}"
        )

        if not dry_run:
            if not isinstance(run_id, int):
                error(f"Cannot delete workflow run with invalid id: {run_id!r}")

            delete_workflow_run(repo, run_id, token)

            if delete_sleep_seconds:
                time.sleep(delete_sleep_seconds)

    print_summary(
        total=total_runs,
        inspected=inspected,
        delete_count=delete_count,
        keep_count=keep_count,
        dry_run=dry_run,
        retention_days=retention_days,
        preserved_count=len(keep_run_ids),
        delete_cap_reached=delete_cap_reached,
    )


if __name__ == "__main__":
    main()
