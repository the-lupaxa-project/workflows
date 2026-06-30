#!/usr/bin/env python3
"""
Cleanup old GitHub Actions workflow runs.

Deletes completed workflow runs older than the configured retention period,
while preserving selected representative runs per workflow.

Safe behaviour:
  - Never deletes the current cleanup run.
  - Never deletes non-completed runs.
  - Supports dry-run mode.
  - Keeps latest successful/failed/cancelled/timed_out runs per workflow.
  - Can keep the last N successful runs per workflow.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple
from urllib.error import HTTPError, URLError


DEFAULT_RETENTION_DAYS = 90
DEFAULT_PER_PAGE = 100


def error(message: str, *, code: int = 1) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
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
            print(body, file=sys.stderr)
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

        url = next_url

    return runs


def workflow_key(run: Dict[str, Any]) -> str:
    workflow_id = run.get("workflow_id")
    if workflow_id is not None:
        return str(workflow_id)

    path = str(run.get("path") or "")
    if path:
        return path

    name = str(run.get("name") or "unknown")
    return name


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


def run_conclusion(run: Dict[str, Any]) -> str:
    return str(run.get("conclusion") or "").strip().lower()


def run_status(run: Dict[str, Any]) -> str:
    return str(run.get("status") or "").strip().lower()


def find_keep_run_ids(
    runs: List[Dict[str, Any]],
    *,
    keep_latest_successful: bool,
    keep_latest_failed: bool,
    keep_latest_cancelled: bool,
    keep_latest_timed_out: bool,
    keep_last_n_successful: int,
) -> Set[int]:
    keep_ids: Set[int] = set()

    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for run in runs:
        if run_status(run) != "completed":
            continue

        key = workflow_key(run)
        grouped.setdefault(key, []).append(run)

    for workflow_runs in grouped.values():
        completed_sorted = sorted(
            workflow_runs,
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

    created_at = run_created_at(run)
    if created_at >= cutoff:
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
) -> None:
    print("Workflow run cleanup configuration")
    print("==================================")
    print(f"Mode: {'DRY RUN' if dry_run else 'DELETE'}")
    print(f"Retention days: {retention_days}")
    print(f"Keep latest successful: {keep_latest_successful}")
    print(f"Keep latest failed: {keep_latest_failed}")
    print(f"Keep latest cancelled: {keep_latest_cancelled}")
    print(f"Keep latest timed out: {keep_latest_timed_out}")
    print(f"Keep last N successful: {keep_last_n_successful}")
    print(f"Delete skipped: {delete_skipped}")
    print(f"Delete neutral: {delete_neutral}")
    print()


def print_summary(
    *,
    total: int,
    delete_count: int,
    keep_count: int,
    dry_run: bool,
    retention_days: int,
    preserved_count: int,
) -> None:
    print()
    print("Workflow run cleanup summary")
    print("============================")
    print(f"Mode: {'DRY RUN' if dry_run else 'DELETE'}")
    print(f"Retention days: {retention_days}")
    print(f"Workflow runs inspected: {total}")
    print(f"Preserved representative runs: {preserved_count}")
    print(f"Runs selected for deletion: {delete_count}")
    print(f"Runs kept/skipped: {keep_count}")


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
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    runs = fetch_all_workflow_runs(repo, token)

    keep_run_ids = find_keep_run_ids(
        runs,
        keep_latest_successful=keep_latest_successful,
        keep_latest_failed=keep_latest_failed,
        keep_latest_cancelled=keep_latest_cancelled,
        keep_latest_timed_out=keep_latest_timed_out,
        keep_last_n_successful=keep_last_n_successful,
    )

    delete_count = 0
    keep_count = 0

    for run in sorted(runs, key=run_created_at):
        run_id = run.get("id")
        name = str(run.get("name") or "unknown")
        path = str(run.get("path") or "")
        status = run_status(run)
        conclusion = run_conclusion(run)
        created_at = str(run.get("created_at") or "")

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
            print(
                f"[KEEP]   {run_id} | {created_at} | {name} | "
                f"{status}/{conclusion} | {reason}"
            )
            continue

        delete_count += 1
        print(
            f"[DELETE] {run_id} | {created_at} | {name} | "
            f"{status}/{conclusion} | {path}"
        )

        if not dry_run:
            if not isinstance(run_id, int):
                error(f"Cannot delete workflow run with invalid id: {run_id!r}")

            delete_workflow_run(repo, run_id, token)

    print_summary(
        total=len(runs),
        delete_count=delete_count,
        keep_count=keep_count,
        dry_run=dry_run,
        retention_days=retention_days,
        preserved_count=len(keep_run_ids),
    )


if __name__ == "__main__":
    main()
