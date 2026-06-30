#!/usr/bin/env python3
"""
Delete old GitHub Actions workflow runs, while preserving the latest
successful completed run for each workflow.

Safe defaults:
  - Dry-run unless CLEANUP_WORKFLOW_RUNS_DRY_RUN=false.
  - Never deletes the current workflow run.
  - Never deletes queued, in_progress, requested, waiting, or pending runs.
  - Keeps the latest successful completed run per workflow_id.
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
        body = (
            exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        )
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
        f"https://api.github.com/repos/{repo}/actions/runs?per_page={DEFAULT_PER_PAGE}"
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


def find_latest_successful_runs(runs: List[Dict[str, Any]]) -> Set[int]:
    latest_by_workflow: Dict[str, Dict[str, Any]] = {}

    for run in runs:
        status = str(run.get("status") or "").lower()
        conclusion = str(run.get("conclusion") or "").lower()

        if status != "completed" or conclusion != "success":
            continue

        key = workflow_key(run)
        existing = latest_by_workflow.get(key)

        if existing is None or run_created_at(run) > run_created_at(existing):
            latest_by_workflow[key] = run

    keep_ids: Set[int] = set()

    for run in latest_by_workflow.values():
        run_id = run.get("id")
        if isinstance(run_id, int):
            keep_ids.add(run_id)

    return keep_ids


def should_delete_run(
    run: Dict[str, Any],
    *,
    cutoff: datetime,
    current_run_id: str,
    keep_run_ids: Set[int],
) -> Tuple[bool, str]:
    run_id = run.get("id")
    status = str(run.get("status") or "").lower()

    if str(run_id) == current_run_id:
        return False, "current cleanup run"

    if isinstance(run_id, int) and run_id in keep_run_ids:
        return False, "latest successful run for workflow"

    if status != "completed":
        return False, f"not completed: {status}"

    created_at = run_created_at(run)
    if created_at >= cutoff:
        return False, "newer than cutoff"

    return True, "old completed run"


def delete_workflow_run(repo: str, run_id: int, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    _data, _next_url, status = github_request(url, token, method="DELETE")

    if status not in (204, 202):
        error(f"Unexpected HTTP {status} deleting workflow run {run_id}")


def print_summary(
    *,
    total: int,
    delete_count: int,
    keep_count: int,
    dry_run: bool,
    retention_days: int,
) -> None:
    mode = "DRY RUN" if dry_run else "DELETE"
    print()
    print("Workflow run cleanup summary")
    print("============================")
    print(f"Mode: {mode}")
    print(f"Retention days: {retention_days}")
    print(f"Workflow runs inspected: {total}")
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

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)

    runs = fetch_all_workflow_runs(repo, token)
    keep_run_ids = find_latest_successful_runs(runs)

    delete_count = 0
    keep_count = 0

    for run in sorted(runs, key=run_created_at):
        run_id = run.get("id")
        name = str(run.get("name") or "unknown")
        path = str(run.get("path") or "")
        status = str(run.get("status") or "")
        conclusion = str(run.get("conclusion") or "")
        created_at = str(run.get("created_at") or "")

        should_delete, reason = should_delete_run(
            run,
            cutoff=cutoff,
            current_run_id=current_run_id,
            keep_run_ids=keep_run_ids,
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
    )


if __name__ == "__main__":
    main()
