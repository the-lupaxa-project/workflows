#!/usr/bin/env python3
"""Optional Slack notifications for CodeQL / Code Scanning alert changes.

Compares GitHub Code Scanning alert state before and after analysis.
Slack delivery is best-effort and must never fail the CodeQL job.
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
from pathlib import Path
from typing import Any

Alert = dict[str, Any]
Changes = dict[str, list[Alert]]

MAX_ALERTS_IN_SLACK = 10
DEFAULT_WAIT_ATTEMPTS = 12
DEFAULT_WAIT_INTERVAL_SECONDS = 5
API_PAGE_SIZE = 100


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _github_api(path: str, *, params: dict[str, str] | None = None) -> Any:
    token = _env("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for Code Scanning API access")

    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = f"https://api.github.com{path}{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lupaxa-codeql-slack-notify",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_code_scanning_alerts(repository: str) -> list[Alert]:
    """Fetch all Code Scanning alerts for a repository (handles pagination)."""
    owner, _, repo = repository.partition("/")
    if not owner or not repo:
        raise ValueError(f"Invalid repository: {repository!r}")

    alerts: list[Alert] = []
    page = 1
    while True:
        try:
            batch = _github_api(
                f"/repos/{owner}/{repo}/code-scanning/alerts",
                params={
                    "per_page": str(API_PAGE_SIZE),
                    "page": str(page),
                    # Include open/dismissed/fixed so comparisons can see history.
                    "state": "all",
                },
            )
        except urllib.error.HTTPError as exc:
            # No prior Code Scanning setup / empty history.
            if exc.code in {404, 403} and page == 1:
                return []
            raise
        if not isinstance(batch, list):
            raise TypeError("Unexpected Code Scanning alerts API response")
        if not batch:
            break
        alerts.extend(batch)
        if len(batch) < API_PAGE_SIZE:
            break
        page += 1
    return alerts


def save_snapshot(path: str, alerts: list[Alert]) -> None:
    Path(path).write_text(
        json.dumps(alerts, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_snapshot(path: str) -> list[Alert]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError(f"Snapshot {path} must contain a JSON list")
    return data


def index_alerts(alerts: list[Alert]) -> dict[int, Alert]:
    indexed: dict[int, Alert] = {}
    for alert in alerts:
        number = alert.get("number")
        if isinstance(number, int):
            indexed[number] = alert
    return indexed


def _state(alert: Alert) -> str:
    return str(alert.get("state") or "").lower()


def compare_alerts(before: list[Alert], after: list[Alert]) -> Changes:
    """Compare alert snapshots and return new / fixed / reappeared lists."""
    before_idx = index_alerts(before)
    after_idx = index_alerts(after)

    new: list[Alert] = []
    fixed: list[Alert] = []
    reappeared: list[Alert] = []

    for number, after_alert in after_idx.items():
        if _state(after_alert) != "open":
            continue
        before_alert = before_idx.get(number)
        if before_alert is None:
            new.append(after_alert)
            continue
        before_state = _state(before_alert)
        if before_state == "open":
            continue
        if before_state == "fixed":
            reappeared.append(after_alert)
        else:
            # Previously known non-open alert (e.g. dismissed) that is open again.
            reappeared.append(after_alert)

    for number, before_alert in before_idx.items():
        if _state(before_alert) != "open":
            continue
        maybe_after = after_idx.get(number)
        if maybe_after is None:
            continue
        if _state(maybe_after) == "fixed":
            fixed.append(maybe_after)

    new.sort(key=lambda alert: int(alert.get("number") or 0))
    fixed.sort(key=lambda alert: int(alert.get("number") or 0))
    reappeared.sort(key=lambda alert: int(alert.get("number") or 0))
    return {"new": new, "fixed": fixed, "reappeared": reappeared}


def format_severity(alert: Alert) -> str:
    rule = alert.get("rule") if isinstance(alert.get("rule"), dict) else {}
    security = rule.get("security_severity_level") if isinstance(rule, dict) else None
    if isinstance(security, str) and security.strip():
        return security.strip().upper()
    severity = rule.get("severity") if isinstance(rule, dict) else None
    if isinstance(severity, str) and severity.strip():
        mapping = {
            "error": "HIGH",
            "warning": "WARNING",
            "note": "NOTE",
            "none": "NOTE",
        }
        key = severity.strip().lower()
        return mapping.get(key, severity.strip().upper())
    return "UNKNOWN"


def format_location(alert: Alert) -> str:
    instance = alert.get("most_recent_instance")
    if not isinstance(instance, dict):
        return "unknown"
    location = instance.get("location")
    if not isinstance(location, dict):
        return "unknown"
    path = location.get("path") or "unknown"
    start_line = location.get("start_line")
    if isinstance(start_line, int):
        return f"{path}:{start_line}"
    return str(path)


def _rule_id(alert: Alert) -> str:
    rule = alert.get("rule") if isinstance(alert.get("rule"), dict) else {}
    rule_id = rule.get("id") if isinstance(rule, dict) else None
    return str(rule_id or "unknown-rule")


def _alert_lines(alerts: list[Alert], *, location_label: str = "Location") -> list[str]:
    lines: list[str] = []
    shown = alerts[:MAX_ALERTS_IN_SLACK]
    for alert in shown:
        lines.append(
            f"*{format_severity(alert)}*  "
            f"#{alert.get('number')} `{_rule_id(alert)}`\n"
            f"{location_label}: `{format_location(alert)}`\n"
            f"<{alert.get('html_url')}|View alert>"
        )
    remaining = len(alerts) - len(shown)
    if remaining > 0:
        lines.append(f"_…and {remaining} more_")
    return lines


def build_slack_payload(
    repository: str,
    branch: str,
    changes: Changes,
) -> dict[str, Any]:
    new = changes.get("new") or []
    fixed = changes.get("fixed") or []
    reappeared = changes.get("reappeared") or []

    header_bits: list[str] = []
    if new:
        header_bits.append(f"🚨 New: {len(new)}")
    if fixed:
        header_bits.append(f"✅ Fixed: {len(fixed)}")
    if reappeared:
        header_bits.append(f"🔄 Reappeared: {len(reappeared)}")
    header = " · ".join(header_bits) if header_bits else "CodeQL Alert Changes"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header[:150], "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Repository:* `{repository}`\n"
                    f"*Branch:* `{branch}`\n"
                    f"<{f'https://github.com/{repository}/security/code-scanning'}|Code Scanning overview>"
                ),
            },
        },
    ]

    if new:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🚨 New alerts ({len(new)})*\n" + "\n\n".join(_alert_lines(new)),
                },
            }
        )
    if fixed:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*✅ Fixed alerts ({len(fixed)})*\n"
                        + "\n\n".join(_alert_lines(fixed, location_label="Previous location"))
                    ),
                },
            }
        )
    if reappeared:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*🔄 Reappeared alerts ({len(reappeared)})*\n"
                        + "\n\n".join(_alert_lines(reappeared))
                    ),
                },
            }
        )

    return {"text": header, "blocks": blocks}


def build_failure_payload(
    repository: str,
    branch: str,
    workflow: str,
    run_url: str,
    commit_sha: str,
) -> dict[str, Any]:
    short = commit_sha[:12] if commit_sha else "unknown"
    text = "⚠️ CodeQL Analysis Failed"
    return {
        "text": text,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": text, "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Repository:* `{repository}`\n"
                        f"*Branch:* `{branch}`\n"
                        f"*Workflow:* `{workflow}`\n"
                        f"*Commit:* `{short}`\n"
                        f"CodeQL failed to run — this does *not* mean vulnerabilities were found.\n"
                        f"<{run_url}|View workflow run>"
                    ),
                },
            },
        ],
    }


def send_slack_notification(webhook_url: str, payload: dict[str, Any]) -> None:
    if not webhook_url:
        raise RuntimeError("Slack webhook URL is empty")
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        status = getattr(response, "status", 200)
        if status < 200 or status >= 300:
            raise RuntimeError(f"Slack webhook returned HTTP {status}")


def write_step_summary(changes: Changes, slack_status: str) -> None:
    path = _env("GITHUB_STEP_SUMMARY")
    if not path:
        return
    summary = (
        "## CodeQL Alert Changes\n"
        f"- New: {len(changes.get('new') or [])}\n"
        f"- Fixed: {len(changes.get('fixed') or [])}\n"
        f"- Reappeared: {len(changes.get('reappeared') or [])}\n"
        f"- Slack notification: {slack_status}\n"
    )
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(summary)


def is_default_branch() -> bool:
    current = _env("GITHUB_REF_NAME") or _env("CURRENT_REF_NAME")
    default = _env("DEFAULT_BRANCH")
    if not current or not default:
        return False
    return current == default


def _has_slack_webhook() -> bool:
    return bool(_env("SLACK_WEBHOOK_URL"))


def _analysis_ready(repository: str, commit_sha: str) -> bool:
    owner, _, repo = repository.partition("/")
    if not owner or not repo or not commit_sha:
        return False
    try:
        analyses = _github_api(
            f"/repos/{owner}/{repo}/code-scanning/analyses",
            params={"per_page": "20", "page": "1"},
        )
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 404}:
            return False
        raise
    if not isinstance(analyses, list):
        return False
    for analysis in analyses:
        if not isinstance(analysis, dict):
            continue
        if str(analysis.get("commit_sha") or "") == commit_sha:
            return True
    return False


def cmd_capture(args: argparse.Namespace) -> int:
    repository = args.repository or _env("GITHUB_REPOSITORY")
    if not repository:
        print("::error::GITHUB_REPOSITORY / --repository is required", file=sys.stderr)
        return 1
    alerts = get_code_scanning_alerts(repository)
    save_snapshot(args.output, alerts)
    print(f"Captured {len(alerts)} Code Scanning alert(s) to snapshot")
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    repository = args.repository or _env("GITHUB_REPOSITORY")
    commit_sha = args.commit_sha or _env("GITHUB_SHA")
    attempts = args.attempts
    interval = args.interval
    if not repository or not commit_sha:
        print("::warning::Missing repository or commit SHA; skipping wait")
        return 0

    for attempt in range(1, attempts + 1):
        if _analysis_ready(repository, commit_sha):
            print(f"Code Scanning analysis for {commit_sha[:12]} is available (attempt {attempt})")
            return 0
        if attempt < attempts:
            time.sleep(interval)

    print(
        "::warning::Code Scanning analysis was not visible within the retry limit; "
        "Slack change notifications will be skipped for this run"
    )
    # Non-zero signals caller to skip comparison, but must not fail CodeQL.
    return 2


def cmd_notify(args: argparse.Namespace) -> int:
    repository = args.repository or _env("GITHUB_REPOSITORY")
    branch = args.branch or _env("GITHUB_REF_NAME") or _env("CURRENT_REF_NAME") or "unknown"

    if not is_default_branch():
        print("Not analysing the default branch; skipping lifecycle Slack notifications")
        write_step_summary({"new": [], "fixed": [], "reappeared": []}, "skipped (non-default branch)")
        return 0

    if not _has_slack_webhook():
        print("Slack webhook not configured; skipping notification")
        write_step_summary({"new": [], "fixed": [], "reappeared": []}, "not configured")
        return 0

    before = load_snapshot(args.before)
    after = load_snapshot(args.after)
    changes = compare_alerts(before, after)

    if not (changes["new"] or changes["fixed"] or changes["reappeared"]):
        print("No CodeQL alert lifecycle changes; not sending Slack message")
        write_step_summary(changes, "not sent (no changes)")
        return 0

    payload = build_slack_payload(repository=repository, branch=branch, changes=changes)
    try:
        send_slack_notification(_env("SLACK_WEBHOOK_URL"), payload)
    except Exception as exc:  # noqa: BLE001 - must never fail CodeQL
        print(f"::warning::Slack notification failed: {exc}")
        write_step_summary(changes, "failed")
        return 0

    print(
        "Slack notification sent "
        f"(new={len(changes['new'])}, fixed={len(changes['fixed'])}, "
        f"reappeared={len(changes['reappeared'])})"
    )
    write_step_summary(changes, "sent")
    return 0


def cmd_failure(args: argparse.Namespace) -> int:
    if not is_default_branch():
        print("Not analysing the default branch; skipping failure Slack notification")
        return 0
    if not _has_slack_webhook():
        print("Slack webhook not configured; skipping failure notification")
        return 0

    repository = args.repository or _env("GITHUB_REPOSITORY")
    branch = args.branch or _env("GITHUB_REF_NAME") or _env("CURRENT_REF_NAME") or "unknown"
    workflow = args.workflow or _env("GITHUB_WORKFLOW") or "Code Analysis"
    run_id = _env("GITHUB_RUN_ID")
    run_url = args.run_url or (
        f"https://github.com/{repository}/actions/runs/{run_id}" if repository and run_id else ""
    )
    commit_sha = args.commit_sha or _env("GITHUB_SHA")

    payload = build_failure_payload(
        repository=repository or "unknown",
        branch=branch,
        workflow=workflow,
        run_url=run_url or "https://github.com",
        commit_sha=commit_sha,
    )
    try:
        send_slack_notification(_env("SLACK_WEBHOOK_URL"), payload)
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::Slack failure notification failed: {exc}")
        return 0
    print("Slack failure notification sent")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    capture = sub.add_parser("capture", help="Capture Code Scanning alerts snapshot")
    capture.add_argument("--output", required=True)
    capture.add_argument("--repository")
    capture.set_defaults(func=cmd_capture)

    wait = sub.add_parser("wait", help="Wait for Code Scanning analysis for this commit")
    wait.add_argument("--repository")
    wait.add_argument("--commit-sha")
    wait.add_argument("--attempts", type=int, default=DEFAULT_WAIT_ATTEMPTS)
    wait.add_argument("--interval", type=float, default=DEFAULT_WAIT_INTERVAL_SECONDS)
    wait.set_defaults(func=cmd_wait)

    notify = sub.add_parser("notify", help="Compare snapshots and notify Slack")
    notify.add_argument("--before", required=True)
    notify.add_argument("--after", required=True)
    notify.add_argument("--repository")
    notify.add_argument("--branch")
    notify.set_defaults(func=cmd_notify)

    failure = sub.add_parser("failure", help="Notify Slack that CodeQL failed")
    failure.add_argument("--repository")
    failure.add_argument("--branch")
    failure.add_argument("--workflow")
    failure.add_argument("--run-url")
    failure.add_argument("--commit-sha")
    failure.set_defaults(func=cmd_failure)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - keep CodeQL green
        print(f"::warning::codeql-slack-notify failed: {exc}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
