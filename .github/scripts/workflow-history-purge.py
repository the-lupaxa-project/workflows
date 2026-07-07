#!/usr/bin/env python3
"""
Delete completed GitHub Actions workflow runs for the current repository.

Required environment:
  GITHUB_TOKEN
  GITHUB_REPOSITORY

Optional environment:
  PURGE_DRY_RUN=true|false
  PURGE_LIMIT=0
  PURGE_DELAY_SECONDS=0.25
  PURGE_VERBOSITY=1
  PURGE_RETRIES=3
  PURGE_CONFIRM=false
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


API_BASE = "https://api.github.com"
SKIPPED_STATUSES = {"in_progress", "queued", "waiting", "requested", "pending"}


@dataclass
class Stats:
    inspected: int = 0
    deleted: int = 0
    skipped: int = 0
    failed: int = 0
    retries: int = 0


def parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    normalised = value.strip().lower()
    if normalised in {"1", "true", "yes", "y", "on"}:
        return True
    if normalised in {"0", "false", "no", "n", "off"}:
        return False

    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def env_bool(name: str, default: bool) -> bool:
    return parse_bool(os.getenv(name), default)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"ERROR: required environment variable {name} is not set", file=sys.stderr, flush=True)
        raise SystemExit(2)
    return value


def api_request(
    method: str,
    path: str,
    token: str,
    retries: int,
    stats: Stats,
    body: bytes | None = None,
) -> Any:
    url = f"{API_BASE}{path}"

    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "lupaxa-workflow-history-purge",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 204:
                    return None

                raw = response.read()
                if not raw:
                    return None

                return json.loads(raw.decode("utf-8"))

        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")

            if exc.code in {403, 429, 500, 502, 503, 504} and attempt < retries:
                stats.retries += 1
                sleep_for = min(60, 2**attempt * 5)
                print(
                    f"[RETRY] {method} {url} failed with HTTP {exc.code}; retrying in {sleep_for}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(sleep_for)
                continue

            raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc

        except urllib.error.URLError as exc:
            if attempt < retries:
                stats.retries += 1
                sleep_for = min(60, 2**attempt * 5)
                print(
                    f"[RETRY] {method} {url} failed: {exc}; retrying in {sleep_for}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(sleep_for)
                continue

            raise RuntimeError(f"{method} {url} failed: {exc}") from exc

    raise RuntimeError(f"{method} {url} failed after retries")


def get_workflow_runs_page(
    repository: str,
    token: str,
    retries: int,
    stats: Stats,
    page: int = 1,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"per_page": per_page, "page": page})
    data = api_request(
        "GET",
        f"/repos/{repository}/actions/runs?{query}",
        token,
        retries,
        stats,
    )

    return data.get("workflow_runs", [])


def iter_workflow_runs_for_dry_run(
    repository: str,
    token: str,
    retries: int,
    stats: Stats,
) -> Any:
    page = 1
    per_page = 100

    while True:
        runs = get_workflow_runs_page(
            repository=repository,
            token=token,
            retries=retries,
            stats=stats,
            page=page,
            per_page=per_page,
        )

        if not runs:
            break

        for run in runs:
            yield run

        if len(runs) < per_page:
            break

        page += 1


def delete_run(repository: str, run_id: int, token: str, retries: int, stats: Stats) -> None:
    api_request(
        "DELETE",
        f"/repos/{repository}/actions/runs/{run_id}",
        token,
        retries,
        stats,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete completed GitHub Actions workflow runs for the current repository.",
    )

    parser.add_argument(
        "--dry-run",
        default=env_bool("PURGE_DRY_RUN", True),
        type=lambda value: parse_bool(value, True),
        help="Report what would be deleted without deleting anything. Default: true.",
    )

    parser.add_argument(
        "--limit",
        default=int(os.getenv("PURGE_LIMIT", "0")),
        type=int,
        help="Maximum number of runs to delete. Use 0 for unlimited. Default: 0.",
    )

    parser.add_argument(
        "--delay",
        default=float(os.getenv("PURGE_DELAY_SECONDS", "0.25")),
        type=float,
        help="Delay in seconds between delete requests. Default: 0.25.",
    )

    parser.add_argument(
        "--verbosity",
        default=int(os.getenv("PURGE_VERBOSITY", "1")),
        choices=[0, 1, 2],
        type=int,
        help="Output verbosity: 0 summary only, 1 progress, 2 detailed. Default: 1.",
    )

    parser.add_argument(
        "--retries",
        default=int(os.getenv("PURGE_RETRIES", "3")),
        type=int,
        help="Number of retries for transient API failures. Default: 3.",
    )

    parser.add_argument(
        "--confirm",
        default=env_bool("PURGE_CONFIRM", False),
        action="store_true",
        help="Required when --dry-run=false to confirm destructive deletion.",
    )

    return parser


def should_skip(status: str) -> bool:
    return status in SKIPPED_STATUSES


def print_header(repository: str, dry_run: bool, limit: int, delay: float, retries: int, confirm: bool) -> None:
    print("Workflow History Purge", flush=True)
    print("======================", flush=True)
    print(f"Repository : {repository}", flush=True)
    print(f"Dry run    : {str(dry_run).lower()}", flush=True)
    print(f"Confirm    : {str(confirm).lower()}", flush=True)
    print(f"Limit      : {limit if limit else 'unlimited'}", flush=True)
    print(f"Delay      : {delay}s", flush=True)
    print(f"Retries    : {retries}", flush=True)
    print("", flush=True)


def validate_args(args: argparse.Namespace) -> int:
    if not args.dry_run and not args.confirm:
        print(
            "ERROR: refusing to delete workflow runs without --confirm when --dry-run=false",
            file=sys.stderr,
            flush=True,
        )
        return 2

    if args.limit < 0:
        print("ERROR: --limit must be 0 or greater", file=sys.stderr, flush=True)
        return 2

    if args.delay < 0:
        print("ERROR: --delay must be 0 or greater", file=sys.stderr, flush=True)
        return 2

    if args.retries < 0:
        print("ERROR: --retries must be 0 or greater", file=sys.stderr, flush=True)
        return 2

    return 0


def handle_run(
    *,
    run: dict[str, Any],
    repository: str,
    token: str,
    args: argparse.Namespace,
    stats: Stats,
    candidate_count: int,
) -> tuple[int, bool]:
    stats.inspected += 1

    run_id = int(run["id"])
    name = run.get("name") or "(unnamed workflow)"
    status = run.get("status") or "unknown"
    conclusion = run.get("conclusion") or "none"
    created_at = run.get("created_at") or "unknown"

    if should_skip(status):
        stats.skipped += 1
        if args.verbosity >= 2:
            print(f"[SKIP]   {run_id} | {status:<12} | {created_at} | {name}", flush=True)
        return candidate_count, False

    if status != "completed":
        stats.skipped += 1
        if args.verbosity >= 2:
            print(f"[SKIP]   {run_id} | {status:<12} | {created_at} | {name}", flush=True)
        return candidate_count, False

    if args.limit and candidate_count >= args.limit:
        stats.skipped += 1
        if args.verbosity >= 2:
            print(f"[LIMIT]  {run_id} | {conclusion:<12} | {created_at} | {name}", flush=True)
        return candidate_count, False

    candidate_count += 1

    if args.dry_run:
        stats.skipped += 1
        if args.verbosity >= 1:
            print(f"[DRY]    {candidate_count:>5} | {run_id} | {conclusion:<12} | {name}", flush=True)
        return candidate_count, False

    try:
        delete_run(repository, run_id, token, args.retries, stats)
        stats.deleted += 1

        if args.verbosity >= 1:
            print(f"[DELETE] {candidate_count:>5} | {run_id} | {conclusion:<12} | {name}", flush=True)

        if args.delay > 0:
            time.sleep(args.delay)

        return candidate_count, True

    except RuntimeError as exc:
        stats.failed += 1
        print(f"[FAILED] {run_id} | {name} | {exc}", file=sys.stderr, flush=True)
        return candidate_count, False


def run_dry_run(repository: str, token: str, args: argparse.Namespace, stats: Stats) -> None:
    candidate_count = 0

    for run in iter_workflow_runs_for_dry_run(repository, token, args.retries, stats):
        candidate_count, _ = handle_run(
            run=run,
            repository=repository,
            token=token,
            args=args,
            stats=stats,
            candidate_count=candidate_count,
        )


def run_delete(repository: str, token: str, args: argparse.Namespace, stats: Stats) -> None:
    candidate_count = 0
    pass_number = 0

    while True:
        if args.limit and candidate_count >= args.limit:
            break

        pass_number += 1

        if args.verbosity >= 2:
            print(f"[PASS]   Fetching page 1, pass {pass_number}", flush=True)

        runs = get_workflow_runs_page(
            repository=repository,
            token=token,
            retries=args.retries,
            stats=stats,
            page=1,
            per_page=100,
        )

        if not runs:
            break

        deleted_this_pass = 0
        deletable_seen_this_pass = 0

        for run in runs:
            if args.limit and candidate_count >= args.limit:
                break

            status = run.get("status") or "unknown"
            if status == "completed":
                deletable_seen_this_pass += 1

            before_deleted = stats.deleted

            candidate_count, deleted = handle_run(
                run=run,
                repository=repository,
                token=token,
                args=args,
                stats=stats,
                candidate_count=candidate_count,
            )

            if deleted or stats.deleted > before_deleted:
                deleted_this_pass += 1

        if deleted_this_pass > 0:
            continue

        if deletable_seen_this_pass == 0:
            break

        if args.verbosity >= 1:
            print(
                "[STOP]   No deletions completed during this pass; stopping to avoid an infinite loop.",
                flush=True,
            )
        break


def print_summary(repository: str, args: argparse.Namespace, stats: Stats, started: datetime) -> None:
    elapsed = datetime.now(timezone.utc) - started

    print("", flush=True)
    print("Summary", flush=True)
    print("-------", flush=True)
    print(f"Repository : {repository}", flush=True)
    print(f"Mode       : {'dry-run' if args.dry_run else 'delete'}", flush=True)
    print(f"Confirm    : {str(args.confirm).lower()}", flush=True)
    print(f"Inspected  : {stats.inspected}", flush=True)
    print(f"Deleted    : {stats.deleted}", flush=True)
    print(f"Skipped    : {stats.skipped}", flush=True)
    print(f"Failed     : {stats.failed}", flush=True)
    print(f"Retries    : {stats.retries}", flush=True)
    print(f"Limit      : {args.limit if args.limit else 'unlimited'}", flush=True)
    print(f"Elapsed    : {str(elapsed).split('.')[0]}", flush=True)


def main() -> int:
    args = build_parser().parse_args()

    validation_result = validate_args(args)
    if validation_result:
        return validation_result

    token = require_env("GITHUB_TOKEN")
    repository = require_env("GITHUB_REPOSITORY")

    stats = Stats()
    started = datetime.now(timezone.utc)

    if args.verbosity >= 1:
        print_header(repository, args.dry_run, args.limit, args.delay, args.retries, args.confirm)

    if args.dry_run:
        run_dry_run(repository, token, args, stats)
    else:
        run_delete(repository, token, args, stats)

    print_summary(repository, args, stats, started)

    return 1 if stats.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
