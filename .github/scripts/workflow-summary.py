#!/usr/bin/env python3
"""
GitHub Actions job status summariser.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, NoReturn, Optional, Set, TextIO, Tuple, cast
from urllib.error import HTTPError, URLError


JobRecord = Tuple[str, str, str, str]

EMOJI_SUMMARY = "📊"
EMOJI_SUCCESS = "✅"
EMOJI_FAILURE = "❌"
EMOJI_TIMEOUT = "⏱️"
EMOJI_CANCELLED = "🚫"
EMOJI_SKIPPED = "⏭️"
EMOJI_NEUTRAL = "⚪"
EMOJI_WARNING = "⚠️"
EMOJI_STALE = "🕰️"
EMOJI_RUNNING = "🔄"
EMOJI_OTHER = "❔"
EMOJI_METADATA = "🧾"
EMOJI_WORKFLOW = "🏃"
EMOJI_BRANCH = "🌿"
EMOJI_COMMIT = "🔖"
EMOJI_PR = "🔀"
EMOJI_REPO = "📦"


def error(message: str, *, code: int = 1) -> NoReturn:
    print(f"{EMOJI_WARNING} ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def ordinal_suffix(day: int) -> str:
    if day in (1, 21, 31):
        suffix = "st"
    elif day in (2, 22):
        suffix = "nd"
    elif day in (3, 23):
        suffix = "rd"
    else:
        suffix = "th"
    return f"<sup>{suffix}</sup>"


def build_human_timestamp() -> str:
    now = datetime.now(timezone.utc)
    day = now.day
    return (
        f"{now.strftime('%A')} "
        f"{day}{ordinal_suffix(day)} "
        f"{now.strftime('%B')} "
        f"{now.strftime('%Y')} "
        f"{now.strftime('%H:%M:%S')}"
    )


def md_table_value(value: str) -> str:
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("|", "\\|")
    value = value.replace("\r", " ")
    value = value.replace("\n", " ")
    return value.strip()


def slugify(value: str, *, fallback: str = "unknown") -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-._")
    return value or fallback


def workflow_file_name_from_ref(workflow_ref: str) -> str:
    if not workflow_ref:
        return ""

    path_part = workflow_ref.split("@", 1)[0]
    filename = path_part.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    return stem


def default_summary_filename() -> str:
    workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF", "")
    workflow_file = workflow_file_name_from_ref(workflow_ref)

    workflow_name = os.environ.get("GITHUB_WORKFLOW", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")

    name_parts = [
        "workflow-summary",
        slugify(workflow_file or workflow_name),
        slugify(run_id),
        f"attempt-{slugify(run_attempt)}",
    ]

    return "-".join(part for part in name_parts if part) + ".md"


def short_sha(sha: str) -> str:
    return sha[:7] if sha else ""


def normalise_result(raw_result: str) -> str:
    return str(raw_result or "unknown").strip().lower().replace("-", "_")


def make_link(label: str, url: str) -> str:
    if not label or not url:
        return md_table_value(label or url)
    return f"[{md_table_value(label)}]({url})"


def parse_next_link(link_header: str) -> Optional[str]:
    if not link_header:
        return None

    for part in link_header.split(","):
        section = part.strip()
        match = re.match(r'<([^>]+)>;\s*rel="([^"]+)"', section)
        if not match:
            continue

        url, rel = match.groups()
        if rel == "next":
            return url

    return None


def status_label(key: str) -> str:
    labels = {
        "success": f"{EMOJI_SUCCESS} Successful",
        "failure": f"{EMOJI_FAILURE} Failed",
        "timed_out": f"{EMOJI_TIMEOUT} Timed out",
        "cancelled": f"{EMOJI_CANCELLED} Cancelled",
        "skipped": f"{EMOJI_SKIPPED} Skipped",
        "neutral": f"{EMOJI_NEUTRAL} Neutral",
        "action_required": f"{EMOJI_WARNING} Action required",
        "stale": f"{EMOJI_STALE} Stale",
        "not_completed": f"{EMOJI_RUNNING} Not completed",
        "other": f"{EMOJI_OTHER} Other",
    }
    return labels.get(key, f"{EMOJI_OTHER} {key}")


def section_title(key: str) -> str:
    titles = {
        "success": f"{EMOJI_SUCCESS} Successful jobs",
        "failure": f"{EMOJI_FAILURE} Failed jobs",
        "timed_out": f"{EMOJI_TIMEOUT} Timed out jobs",
        "cancelled": f"{EMOJI_CANCELLED} Cancelled jobs",
        "skipped": f"{EMOJI_SKIPPED} Skipped jobs",
        "neutral": f"{EMOJI_NEUTRAL} Neutral jobs",
        "action_required": f"{EMOJI_WARNING} Action required jobs",
        "stale": f"{EMOJI_STALE} Stale jobs",
        "not_completed": f"{EMOJI_RUNNING} Not completed jobs",
        "other": f"{EMOJI_OTHER} Other statuses",
    }
    return titles.get(key, key)


def _get_github_context_from_env() -> Tuple[str, str, str]:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    token = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("ACTIONS_RUNTIME_TOKEN")
    )

    if not repo or not run_id:
        error("GITHUB_REPOSITORY or GITHUB_RUN_ID not set; cannot call GitHub API.")

    if not token:
        error("GITHUB_TOKEN, GH_TOKEN, or ACTIONS_RUNTIME_TOKEN is not set; cannot call GitHub API.")

    return repo, run_id, token


def _github_api_get_json(url: str, token: str) -> Tuple[Dict[str, Any], Optional[str]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lupaxa-workflow-summary",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body_bytes = resp.read()
            link_header = resp.headers.get("Link", "")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if body:
            print(body, file=sys.stderr, flush=True)
        error(f"GitHub API returned HTTP {exc.code}: {exc.reason}")
    except URLError as exc:
        error(f"Failed to reach GitHub API: {exc.reason}")
    except Exception as exc:
        error(f"Unexpected error when calling GitHub API: {exc}")

    if status != 200:
        body = body_bytes.decode("utf-8", errors="replace")
        print("GitHub API response body:", file=sys.stderr, flush=True)
        print(body, file=sys.stderr, flush=True)
        error(f"GitHub API returned HTTP {status}.")

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        error(f"Failed to decode GitHub API JSON: {exc}")

    if not isinstance(data, dict):
        error("GitHub API returned JSON, but the top-level structure is not an object.")

    return data, parse_next_link(link_header)


def _fetch_jobs_json(repo: str, run_id: str, token: str) -> Dict[str, Any]:
    url: Optional[str] = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    all_jobs: List[Dict[str, Any]] = []

    while url:
        data, next_url = _github_api_get_json(url, token)
        jobs = data.get("jobs")

        if not isinstance(jobs, list):
            error("GitHub jobs API response did not contain a 'jobs' list.")

        for job in jobs:
            if isinstance(job, dict):
                all_jobs.append(job)

        print(f"{EMOJI_WORKFLOW} Loaded {len(all_jobs)} jobs so far", flush=True)
        url = next_url

    return {
        "total_count": len(all_jobs),
        "jobs": all_jobs,
    }


def _maybe_set_commit_message_env(repo: str, run_id: str, token: str) -> None:
    run_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"

    try:
        data, _ = _github_api_get_json(run_url, token)
    except SystemExit:
        return

    head_commit = data.get("head_commit") or {}
    if not isinstance(head_commit, dict):
        return

    message = str(head_commit.get("message") or "").strip()
    if message:
        os.environ["GITHUB_COMMIT_MESSAGE"] = message


def fetch_jobs_json_from_api() -> Dict[str, Any]:
    repo, run_id, token = _get_github_context_from_env()
    jobs_data = _fetch_jobs_json(repo, run_id, token)
    _maybe_set_commit_message_env(repo, run_id, token)
    return jobs_data


def load_jobs_json_from_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        error(f"JSON file not found: {path}")

    if not os.path.isfile(path):
        error(f"JSON path is not a file: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        error(f"JSON in file {path} is invalid: {exc}")
    except OSError as exc:
        error(f"Failed to read JSON file {path}: {exc}")

    if not isinstance(data, dict):
        error(f"Top-level JSON structure in {path} is not an object.")

    return data


def normalise_job_name(raw: str) -> str:
    raw = str(raw or "")
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    return raw.strip()


def parse_ignored_jobs(raw: str) -> Set[str]:
    ignored: Set[str] = set()

    for part in raw.split(","):
        name = normalise_job_name(part)
        if name:
            ignored.add(name.casefold())

    return ignored


def _extract_api_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return None

    records: List[JobRecord] = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        raw_name = str(job.get("name") or "")
        status = str(job.get("status") or "unknown")
        conclusion = str(job.get("conclusion") or "unknown")
        html_url = str(job.get("html_url") or "")

        if status.lower() != "completed":
            conclusion = f"not_completed:{status}"

        records.append((raw_name, conclusion, status, html_url))

    return records


def _extract_needs_jobs(data: Dict[str, Any]) -> Optional[Iterable[JobRecord]]:
    if not isinstance(data, dict):
        return None

    records: List[JobRecord] = []

    for key, value in data.items():
        raw_name = str(key)

        if isinstance(value, dict):
            result = value.get("result") or value.get("conclusion") or "unknown"
            status = value.get("status") or "completed"
        else:
            result = "unknown"
            status = "completed"

        records.append((raw_name, str(result), str(status), ""))

    return records


def bucket_jobs(
    data: Dict[str, Any],
    ignored_job_names: Optional[Set[str]] = None,
) -> Dict[str, List[Tuple[str, str]]]:
    buckets: Dict[str, List[Tuple[str, str]]] = {
        "success": [],
        "failure": [],
        "timed_out": [],
        "cancelled": [],
        "skipped": [],
        "neutral": [],
        "action_required": [],
        "stale": [],
        "not_completed": [],
        "other": [],
    }

    job_records: Optional[Iterable[JobRecord]] = _extract_api_jobs(data)
    if job_records is None:
        job_records = _extract_needs_jobs(data)

    if not job_records:
        error("Unsupported JSON structure for job results.")

    ignored_normalised: Set[str] = set()
    if ignored_job_names:
        ignored_normalised = {name.casefold() for name in ignored_job_names}

    known_buckets = set(buckets)

    for raw_name, raw_result, _raw_status, html_url in job_records:
        job_name = normalise_job_name(raw_name)
        if not job_name:
            continue

        if ignored_normalised and job_name.casefold() in ignored_normalised:
            continue

        result = normalise_result(raw_result)

        if result.startswith("not_completed:"):
            status = result.split(":", 1)[1] or "unknown"
            buckets["not_completed"].append((f"{job_name} ({status})", html_url))
        elif result in known_buckets:
            buckets[result].append((job_name, html_url))
        else:
            buckets["other"].append((f"{job_name}: {result}", html_url))

    return buckets


def maybe_read_pr_metadata() -> Tuple[str, str]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.isfile(event_path):
        return "", ""

    try:
        with open(event_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return "", ""

    if not isinstance(payload, dict):
        return "", ""

    pr = payload.get("pull_request") or {}
    if not isinstance(pr, dict):
        return "", ""

    number = pr.get("number")
    title = pr.get("title")

    if number:
        return str(number), str(title or "")

    return "", ""


def build_run_url(repo: str, run_id: str) -> str:
    if repo and run_id:
        return f"https://github.com/{repo}/actions/runs/{run_id}"
    return ""


def build_commit_url(repo: str, sha: str) -> str:
    if repo and sha:
        return f"https://github.com/{repo}/commit/{sha}"
    return ""


def build_pr_url(repo: str, pr_number: str) -> str:
    if repo and pr_number:
        return f"https://github.com/{repo}/pull/{pr_number}"
    return ""


def print_count_summary(buckets: Dict[str, List[Tuple[str, str]]], out: TextIO) -> None:
    rows = [
        "success",
        "failure",
        "timed_out",
        "cancelled",
        "skipped",
        "neutral",
        "action_required",
        "stale",
        "not_completed",
        "other",
    ]

    print(f"### {EMOJI_SUMMARY} Result summary", file=out)
    print(file=out)
    print("| Status | Count |", file=out)
    print("| :----- | ----: |", file=out)

    for key in rows:
        count = len(buckets.get(key, []))
        print(f"| {status_label(key)} | {count} |", file=out)

    print(file=out)


def print_sorted_section(
    items: List[Tuple[str, str]],
    title: str,
    out: TextIO,
) -> None:
    if not items:
        return

    unique: Dict[str, str] = {}
    for name, url in items:
        if name and name not in unique:
            unique[name] = url

    if not unique:
        return

    print(f"### {title}", file=out)

    for name in sorted(unique, key=str.casefold):
        url = unique[name]
        if url:
            print(f"- [{md_table_value(name)}]({url})", file=out)
        else:
            print(f"- {md_table_value(name)}", file=out)

    print(file=out)


def print_metadata_table(out: TextIO) -> None:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    workflow = os.environ.get("GITHUB_WORKFLOW", "")
    workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF", "")
    workflow_file = workflow_file_name_from_ref(workflow_ref)
    run_number = os.environ.get("GITHUB_RUN_NUMBER", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    actor = os.environ.get("GITHUB_ACTOR", "unknown")
    triggering_actor = os.environ.get("GITHUB_TRIGGERING_ACTOR", "")
    ref_name = os.environ.get("GITHUB_REF_NAME", "")
    sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")

    pr_number, pr_title = maybe_read_pr_metadata()
    generated_at = build_human_timestamp()

    run_url = build_run_url(repo, run_id)
    commit_url = build_commit_url(repo, sha)
    pr_url = build_pr_url(repo, pr_number)

    commit_message = ""
    if pr_title:
        commit_message = pr_title
    else:
        commit = os.environ.get("GITHUB_COMMIT_MESSAGE", "")
        if commit:
            commit_message = commit

    if commit_message:
        commit_message = commit_message.splitlines()[0].strip()

    print(f"### {EMOJI_METADATA} Workflow metadata", file=out)
    print(file=out)
    print("| Field | Value |", file=out)
    print("| :---- | :---- |", file=out)

    print(f"| {EMOJI_REPO} Repository | {md_table_value(repo)} |", file=out)
    print(f"| {EMOJI_WORKFLOW} Workflow | {md_table_value(workflow)} |", file=out)

    if workflow_file:
        print(f"| {EMOJI_WORKFLOW} Workflow file | {md_table_value(workflow_file)} |", file=out)

    print(f"| {EMOJI_WORKFLOW} Run | {make_link(f'#{run_number}', run_url) if run_url else md_table_value(run_number)} |", file=out)
    print(f"| Attempt | {md_table_value(run_attempt)} |", file=out)
    print(f"| Event | {md_table_value(event_name)} |", file=out)
    print(f"| Actor | {md_table_value(actor)} |", file=out)

    if triggering_actor and triggering_actor != actor:
        print(f"| Triggering actor | {md_table_value(triggering_actor)} |", file=out)

    print(f"| {EMOJI_BRANCH} Ref | {md_table_value(ref_name)} |", file=out)

    if sha:
        commit_label = f"`{short_sha(sha)}`"
        print(f"| {EMOJI_COMMIT} Commit | {make_link(commit_label, commit_url) if commit_url else md_table_value(sha)} |", file=out)

    if commit_message:
        print(f"| {EMOJI_COMMIT} Commit message | {md_table_value(commit_message)} |", file=out)

    if pr_number:
        pr_label = f"#{pr_number}: {pr_title}" if pr_title else f"#{pr_number}"
        print(f"| {EMOJI_PR} Pull request | {make_link(pr_label, pr_url) if pr_url else md_table_value(pr_label)} |", file=out)

    print(f"| Generated at (UTC) | {generated_at} |", file=out)
    print(file=out)


def write_markdown_summary(
    buckets: Dict[str, List[Tuple[str, str]]],
    out: TextIO,
) -> None:
    print(f"# {EMOJI_SUMMARY} Job Status Overview", file=out)
    print(file=out)

    print_count_summary(buckets, out)

    for key in (
        "failure",
        "timed_out",
        "cancelled",
        "not_completed",
        "action_required",
        "stale",
        "neutral",
        "skipped",
        "other",
        "success",
    ):
        print_sorted_section(buckets[key], section_title(key), out)

    print_metadata_table(out)


def output_paths() -> List[str]:
    paths: List[str] = []

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    artifact_path = os.environ.get("WORKFLOW_SUMMARY_FILE", "").strip()

    if summary_path:
        paths.append(summary_path)

    if not artifact_path:
        artifact_path = default_summary_filename()
        os.environ["WORKFLOW_SUMMARY_FILE"] = artifact_path

    if artifact_path and artifact_path not in paths:
        paths.append(artifact_path)

    return paths


def write_summaries(buckets: Dict[str, List[Tuple[str, str]]]) -> None:
    paths = output_paths()

    if not paths:
        write_markdown_summary(buckets, sys.stdout)
        return

    for path in paths:
        mode = "a" if path == os.environ.get("GITHUB_STEP_SUMMARY", "").strip() else "w"

        try:
            with open(path, mode, encoding="utf-8") as out:
                write_markdown_summary(buckets, cast(TextIO, out))
        except OSError as exc:
            error(f"Failed to write summary file {path}: {exc}")


def main() -> None:
    if len(sys.argv) == 2:
        data = load_jobs_json_from_file(sys.argv[1])
    elif len(sys.argv) > 2:
        error("Usage: workflow-summary.py [jobs.json]")
    else:
        data = fetch_jobs_json_from_api()

    raw_ignored_jobs = os.environ.get("WORKFLOW_IGNORE_JOBS", "")
    ignored_job_names: Optional[Set[str]] = None

    if raw_ignored_jobs.strip():
        ignored_job_names = parse_ignored_jobs(raw_ignored_jobs)

    buckets = bucket_jobs(data, ignored_job_names=ignored_job_names)
    write_summaries(buckets)


if __name__ == "__main__":
    main()
