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
  PURGE_YES=false
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
        print(f"ERROR: required environment variable {name} is not set", file=sys.stderr)
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
                sleep_for = min(60, 2 ** attempt * 5)
                print(
                    f"[RETRY] {method} {url} failed with HTTP {exc.code}; retrying in {sleep_for}s",
                    file=sys.stderr,
                )
                time.sleep(sleep_for)
                continue

            raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc

        except urllib.error.URLError as exc:
            if attempt < retries:
                stats.retries += 1
                sleep_for = min(60, 2 ** attempt * 5)
                print(
                    f"[RETRY] {method} {url} failed: {exc}; retrying in {sleep_for}s",
                    file=sys.stderr,
                )
                time.sleep(sleep_for)
                continue

            raise RuntimeError(f"{method} {url} failed: {exc}") from exc

    raise RuntimeError(f"{method} {url} failed after retries")


def iter_workflow_runs(repository: str, token: str, retries: int, stats: Stats) -> Any:
    page = 1
    per_page = 100

    while True:
        query = urllib.parse.urlencode({"per_page": per_page, "page": page})
        data = api_request(
            "GET",
            f"/repos/{repository}/actions/runs?{query}",
            token,
            retries,
            stats,
        )

        runs = data.get("workflow_runs", [])
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
        description="Delete all completed GitHub Actions workflow runs for the current repository.",
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
        "--yes",
        default=env_bool("PURGE_YES", False),
        action="store_true",
        help="Required when --dry-run=false to confirm destructive deletion.",
    )

    return parser


def should_skip(status: str) -> bool:
    return status in SKIPPED_STATUSES


def print_header(repository: str, dry_run: bool, limit: int, delay: float, retries: int) -> None:
    print("Workflow History Purge")
    print("======================")
    print(f"Repository : {repository}")
    print(f"Dry run    : {str(dry_run).lower()}")
    print(f"Limit      : {limit if limit else 'unlimited'}")
    print(f"Delay      : {delay}s")
    print(f"Retries    : {retries}")
    print("")


def main() -> int:
    args = build_parser().parse_args()

    token = require_env("GITHUB_TOKEN")
    repository = require_env("GITHUB_REPOSITORY")
    stats = Stats()
    started = datetime.now(timezone.utc)

    if not args.dry_run and not args.yes:
        print(
            "ERROR: refusing to delete workflow runs without --yes when --dry-run=false",
            file=sys.stderr,
        )
        return 2

    if args.limit < 0:
        print("ERROR: --limit must be 0 or greater", file=sys.stderr)
        return 2

    if args.delay < 0:
        print("ERROR: --delay must be 0 or greater", file=sys.stderr)
        return 2

    if args.retries < 0:
        print("ERROR: --retries must be 0 or greater", file=sys.stderr)
        return 2

    if args.verbosity >= 1:
        print_header(repository, args.dry_run, args.limit, args.delay, args.retries)

    delete_count = 0

    for run in iter_workflow_runs(repository, token, args.retries, stats):
        stats.inspected += 1

        run_id = int(run["id"])
        name = run.get("name") or "(unnamed workflow)"
        status = run.get("status") or "unknown"
        conclusion = run.get("conclusion") or "none"
        created_at = run.get("created_at") or "unknown"

        if should_skip(status):
            stats.skipped += 1
            if args.verbosity >= 2:
                print(f"[SKIP]   {run_id} | {status:<12} | {created_at} | {name}")
            continue

        if status != "completed":
            stats.skipped += 1
            if args.verbosity >= 2:
                print(f"[SKIP]   {run_id} | {status:<12} | {created_at} | {name}")
            continue

        if args.limit and delete_count >= args.limit:
            stats.skipped += 1
            if args.verbosity >= 2:
                print(f"[LIMIT]  {run_id} | {conclusion:<12} | {created_at} | {name}")
            continue

        if args.dry_run:
            stats.skipped += 1
            delete_count += 1
            if args.verbosity >= 1:
                print(f"[DRY]    {delete_count:>5} | {run_id} | {conclusion:<12} | {name}")
            continue

        try:
            delete_run(repository, run_id, token, args.retries, stats)
            stats.deleted += 1
            delete_count += 1

            if args.verbosity >= 1:
                print(f"[DELETE] {delete_count:>5} | {run_id} | {conclusion:<12} | {name}")

            if args.delay > 0:
                time.sleep(args.delay)

        except RuntimeError as exc:
            stats.failed += 1
            print(f"[FAILED] {run_id} | {name} | {exc}", file=sys.stderr)

    elapsed = datetime.now(timezone.utc) - started

    print("")
    print("Summary")
    print("-------")
    print(f"Repository : {repository}")
    print(f"Mode       : {'dry-run' if args.dry_run else 'delete'}")
    print(f"Inspected  : {stats.inspected}")
    print(f"Deleted    : {stats.deleted}")
    print(f"Skipped    : {stats.skipped}")
    print(f"Failed     : {stats.failed}")
    print(f"Retries    : {stats.retries}")
    print(f"Limit      : {args.limit if args.limit else 'unlimited'}")
    print(f"Elapsed    : {str(elapsed).split('.')[0]}")

    return 1 if stats.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
