#!/usr/bin/env python3
"""
Cleanup old GitHub Actions workflow runs and, optionally, old artifacts.
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


Run = Dict[str, Any]
Artifact = Dict[str, Any]


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


def slugify(value: str, *, fallback: str = "unknown") -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-._")
    return value or fallback


def md_value(value: str) -> str:
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("|", "\\|")
    value = value.replace("\r", " ")
    value = value.replace("\n", " ")
    return value.strip()


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


def fetch_all_workflow_runs(repo: str, token: str) -> List[Run]:
    url: Optional[str] = (
        f"https://api.github.com/repos/{repo}/actions/runs"
        f"?per_page={DEFAULT_PER_PAGE}"
    )

    runs: List[Run] = []

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


def fetch_all_artifacts(repo: str, token: str) -> List[Artifact]:
    url: Optional[str] = (
        f"https://api.github.com/repos/{repo}/actions/artifacts"
        f"?per_page={DEFAULT_PER_PAGE}"
    )

    artifacts: List[Artifact] = []

    while url:
        data, next_url, _status = github_request(url, token)

        if data is None:
            break

        page_artifacts = data.get("artifacts", [])

        if isinstance(page_artifacts, list):
            for artifact in page_artifacts:
                if isinstance(artifact, dict):
                    artifacts.append(artifact)

        log(f"[FETCH] Loaded {len(artifacts)} artifacts so far")
        url = next_url

    return artifacts


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


def run_id_as_int(run: Run) -> Optional[int]:
    run_id = run.get("id")
    if isinstance(run_id, int):
        return run_id

    return None


def artifact_id_as_int(artifact: Artifact) -> Optional[int]:
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


def keep_latest_by_conclusion(
    runs: List[Run],
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
    runs: List[Run],
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
    keep_ids: Set[int] = set()
    grouped: Dict[str, List[Run]] = {}

    for run in runs:
        if run_status(run) != "completed":
            continue

        if run_head_branch(run) != preserve_branch:
            continue

        grouped.setdefault(workflow_key(run), []).append(run)

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
    expired = artifact.get("expired")
    if expired is True:
        return True, "artifact already expired"

    if artifact_created_at(artifact) >= artifact_cutoff:
        return False, "artifact newer than cutoff"

    return True, "old artifact"


def delete_workflow_run(repo: str, run_id: int, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    _data, _next_url, status = github_request(url, token, method="DELETE")

    if status not in (202, 204):
        error(f"Unexpected HTTP {status} deleting workflow run {run_id}")


def delete_artifact(repo: str, artifact_id: int, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}"
    _data, _next_url, status = github_request(url, token, method="DELETE")

    if status not in (202, 204):
        error(f"Unexpected HTTP {status} deleting artifact {artifact_id}")


def default_report_filename(repo: str) -> str:
    run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    repo_slug = slugify(repo.replace("/", "-"))
    return f"cleanup-workflow-runs-{repo_slug}-{run_id}-attempt-{run_attempt}.md"


def report_paths(repo: str) -> List[Path]:
    paths: List[Path] = []

    report_file = os.environ.get("CLEANUP_WORKFLOW_RUNS_REPORT_FILE", "").strip()
    if not report_file:
        report_file = default_report_filename(repo)
        os.environ["CLEANUP_WORKFLOW_RUNS_REPORT_FILE"] = report_file

    paths.append(Path(report_file))

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if step_summary:
        step_summary_path = Path(step_summary)
        if step_summary_path not in paths:
            paths.append(step_summary_path)

    return paths


def write_markdown_report(
    repo: str,
    config: Dict[str, Any],
    run_actions: List[Dict[str, str]],
    artifact_actions: List[Dict[str, str]],
    workflow_totals: Dict[str, Dict[str, int]],
    summary: Dict[str, Any],
) -> None:
    for path in report_paths(repo):
        mode = "a" if str(path) == os.environ.get("GITHUB_STEP_SUMMARY", "").strip() else "w"

        with path.open(mode, encoding="utf-8") as out:
            print("## Workflow Run Cleanup Report", file=out)
            print(file=out)

            print("### Summary", file=out)
            print(file=out)
            print("| Field | Value |", file=out)
            print("| :---- | :---- |", file=out)
            for key, value in summary.items():
                print(f"| {md_value(key)} | {md_value(str(value))} |", file=out)
            print(file=out)

            print("### Configuration", file=out)
            print(file=out)
            print("| Field | Value |", file=out)
            print("| :---- | :---- |", file=out)
            for key, value in config.items():
                print(f"| {md_value(key)} | {md_value(str(value))} |", file=out)
            print(file=out)

            print("### Per-workflow totals", file=out)
            print(file=out)
            print("| Workflow | Deleted | Kept |", file=out)
            print("| :------- | ------: | ---: |", file=out)
            for workflow, totals in sorted(workflow_totals.items(), key=lambda item: item[0].casefold()):
                print(
                    f"| {md_value(workflow)} | {totals.get('deleted', 0)} | {totals.get('kept', 0)} |",
                    file=out,
                )
            print(file=out)

            print("### Workflow run actions", file=out)
            print(file=out)
            print("| Action | Run ID | Created | Workflow | Branch | Status | Reason |", file=out)
            print("| :----- | :----- | :------ | :------- | :----- | :----- | :----- |", file=out)
            for item in run_actions:
                print(
                    "| "
                    f"{md_value(item['action'])} | "
                    f"{md_value(item['id'])} | "
                    f"{md_value(item['created'])} | "
                    f"{md_value(item['workflow'])} | "
                    f"{md_value(item['branch'])} | "
                    f"{md_value(item['status'])} | "
                    f"{md_value(item['reason'])} |",
                    file=out,
                )
            print(file=out)

            if artifact_actions:
                print("### Artifact actions", file=out)
                print(file=out)
                print("| Action | Artifact ID | Created | Name | Size | Reason |", file=out)
                print("| :----- | :---------- | :------ | :--- | ---: | :----- |", file=out)
                for item in artifact_actions:
                    print(
                        "| "
                        f"{md_value(item['action'])} | "
                        f"{md_value(item['id'])} | "
                        f"{md_value(item['created'])} | "
                        f"{md_value(item['name'])} | "
                        f"{md_value(item['size'])} | "
                        f"{md_value(item['reason'])} |",
                        file=out,
                    )
                print(file=out)


def print_config(config: Dict[str, Any]) -> None:
    log("Workflow run cleanup configuration")
    log("==================================")
    for key, value in config.items():
        log(f"{key}: {value}")
    log()


def should_log_action(verbosity: str, action: str) -> bool:
    if verbosity == "quiet":
        return False

    if verbosity == "normal":
        return action == "DELETE"

    return True


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

    artifact_retention_days = parse_int(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_ARTIFACT_RETENTION_DAYS", ""),
        default=DEFAULT_ARTIFACT_RETENTION_DAYS,
    )
    if artifact_retention_days < 1:
        error("CLEANUP_WORKFLOW_RUNS_ARTIFACT_RETENTION_DAYS must be at least 1.")

    dry_run = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_DRY_RUN", ""),
        default=True,
    )

    cleanup_artifacts = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_CLEANUP_ARTIFACTS", ""),
        default=False,
    )

    preserve_branch = (
        os.environ.get("CLEANUP_WORKFLOW_RUNS_PRESERVE_BRANCH", "").strip()
        or DEFAULT_PRESERVE_BRANCH
    )

    force_delete_non_default_branch = parse_bool(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_FORCE_DELETE_NON_DEFAULT_BRANCH", ""),
        default=False,
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

    max_artifact_deletes_per_run = parse_int(
        os.environ.get("CLEANUP_WORKFLOW_RUNS_MAX_ARTIFACT_DELETES", ""),
        default=DEFAULT_MAX_ARTIFACT_DELETES_PER_RUN,
    )
    if max_artifact_deletes_per_run < 0:
        error("CLEANUP_WORKFLOW_RUNS_MAX_ARTIFACT_DELETES must be 0 or greater.")

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

    verbosity = os.environ.get("CLEANUP_WORKFLOW_RUNS_VERBOSITY", DEFAULT_VERBOSITY).strip().lower()
    if verbosity not in ("quiet", "normal", "verbose"):
        verbosity = DEFAULT_VERBOSITY

    config: Dict[str, Any] = {
        "Mode": "DRY RUN" if dry_run else "DELETE",
        "Retention days": retention_days,
        "Artifact retention days": artifact_retention_days,
        "Cleanup artifacts": cleanup_artifacts,
        "Preserve branch": preserve_branch,
        "Force delete non-default branch": force_delete_non_default_branch,
        "Keep latest successful": keep_latest_successful,
        "Keep latest failed": keep_latest_failed,
        "Keep latest cancelled": keep_latest_cancelled,
        "Keep latest timed out": keep_latest_timed_out,
        "Keep last N successful": keep_last_n_successful,
        "Delete skipped": delete_skipped,
        "Delete neutral": delete_neutral,
        "Max deletes per run": max_deletes_per_run,
        "Max artifact deletes per run": max_artifact_deletes_per_run,
        "Delete sleep seconds": delete_sleep_seconds,
        "Progress every": progress_every,
        "Verbosity": verbosity,
    }

    if verbosity != "quiet":
        print_config(config)

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    artifact_cutoff = datetime.now(timezone.utc) - timedelta(days=artifact_retention_days)

    runs = fetch_all_workflow_runs(repo, token)

    keep_run_ids = find_keep_run_ids(
        runs,
        preserve_branch=preserve_branch,
        keep_latest_successful=keep_latest_successful,
        keep_latest_failed=keep_latest_failed,
        keep_latest_cancelled=keep_latest_cancelled,
        keep_latest_timed_out=keep_latest_timed_out,
        keep_last_n_successful=keep_last_n_successful,
    )

    run_actions: List[Dict[str, str]] = []
    artifact_actions: List[Dict[str, str]] = []
    workflow_totals: Dict[str, Dict[str, int]] = {}

    run_delete_count = 0
    run_keep_count = 0
    inspected_runs = 0
    run_delete_cap_reached = False
    total_runs = len(runs)

    for run in sorted(runs, key=run_created_at):
        inspected_runs += 1

        run_id = run.get("id")
        workflow = workflow_display(run)
        branch = run_head_branch(run)
        status = run_status(run)
        conclusion = run_conclusion(run)
        created_at = str(run.get("created_at") or "")

        if progress_every and inspected_runs % progress_every == 0:
            log(
                f"[PROGRESS] inspected runs {inspected_runs}/{total_runs}, "
                f"deleted {run_delete_count}, kept/skipped {run_keep_count}"
            )

        should_delete, reason = should_delete_run(
            run,
            cutoff=cutoff,
            current_run_id=current_run_id,
            keep_run_ids=keep_run_ids,
            preserve_branch=preserve_branch,
            force_delete_non_default_branch=force_delete_non_default_branch,
            delete_skipped=delete_skipped,
            delete_neutral=delete_neutral,
        )

        workflow_totals.setdefault(workflow, {"deleted": 0, "kept": 0})

        if not should_delete:
            run_keep_count += 1
            workflow_totals[workflow]["kept"] += 1
            action = "KEEP"
        elif max_deletes_per_run and run_delete_count >= max_deletes_per_run:
            run_keep_count += 1
            workflow_totals[workflow]["kept"] += 1
            run_delete_cap_reached = True
            action = "KEEP"
            reason = "delete cap reached"
        else:
            run_delete_count += 1
            workflow_totals[workflow]["deleted"] += 1
            action = "DELETE"

        if should_log_action(verbosity, action):
            log(
                f"[{action}] {run_id} | {created_at} | {workflow} | "
                f"{branch} | {status}/{conclusion} | {reason}"
            )

        run_actions.append(
            {
                "action": action,
                "id": str(run_id),
                "created": created_at,
                "workflow": workflow,
                "branch": branch,
                "status": f"{status}/{conclusion}",
                "reason": reason,
            }
        )

        if action == "DELETE" and not dry_run:
            if not isinstance(run_id, int):
                error(f"Cannot delete workflow run with invalid id: {run_id!r}")

            delete_workflow_run(repo, run_id, token)

            if delete_sleep_seconds:
                time.sleep(delete_sleep_seconds)

    artifact_delete_count = 0
    artifact_keep_count = 0
    artifact_delete_cap_reached = False
    total_artifacts = 0

    if cleanup_artifacts:
        artifacts = fetch_all_artifacts(repo, token)
        total_artifacts = len(artifacts)

        for artifact in sorted(artifacts, key=artifact_created_at):
            artifact_id = artifact.get("id")
            name = str(artifact.get("name") or "unknown")
            size = str(artifact.get("size_in_bytes") or "0")
            created_at = str(artifact.get("created_at") or "")

            should_delete, reason = should_delete_artifact(
                artifact,
                artifact_cutoff=artifact_cutoff,
            )

            if not should_delete:
                artifact_keep_count += 1
                action = "KEEP"
            elif max_artifact_deletes_per_run and artifact_delete_count >= max_artifact_deletes_per_run:
                artifact_keep_count += 1
                artifact_delete_cap_reached = True
                action = "KEEP"
                reason = "artifact delete cap reached"
            else:
                artifact_delete_count += 1
                action = "DELETE"

            if should_log_action(verbosity, action):
                log(f"[ARTIFACT {action}] {artifact_id} | {created_at} | {name} | {reason}")

            artifact_actions.append(
                {
                    "action": action,
                    "id": str(artifact_id),
                    "created": created_at,
                    "name": name,
                    "size": size,
                    "reason": reason,
                }
            )

            if action == "DELETE" and not dry_run:
                if not isinstance(artifact_id, int):
                    error(f"Cannot delete artifact with invalid id: {artifact_id!r}")

                delete_artifact(repo, artifact_id, token)

                if delete_sleep_seconds:
                    time.sleep(delete_sleep_seconds)

    summary: Dict[str, Any] = {
        "Repository": repo,
        "Mode": "DRY RUN" if dry_run else "DELETE",
        "Workflow runs fetched": total_runs,
        "Workflow runs inspected": inspected_runs,
        "Workflow runs selected for deletion": run_delete_count,
        "Workflow runs kept/skipped": run_keep_count,
        "Preserved representative runs": len(keep_run_ids),
        "Workflow run delete cap reached": run_delete_cap_reached,
        "Artifacts fetched": total_artifacts,
        "Artifacts selected for deletion": artifact_delete_count,
        "Artifacts kept/skipped": artifact_keep_count,
        "Artifact delete cap reached": artifact_delete_cap_reached,
    }

    write_markdown_report(
        repo=repo,
        config=config,
        run_actions=run_actions,
        artifact_actions=artifact_actions,
        workflow_totals=workflow_totals,
        summary=summary,
    )

    log()
    log("Workflow run cleanup summary")
    log("============================")
    for key, value in summary.items():
        log(f"{key}: {value}")


if __name__ == "__main__":
    main()
