"""Unit tests for CodeQL alert comparison used by Slack notifications."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "scripts" / "codeql-slack-notify.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codeql_slack_notify", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["codeql_slack_notify"] = module
    spec.loader.exec_module(module)
    return module


def _alert(
    number: int,
    state: str,
    *,
    rule_id: str = "py/example",
    description: str | None = "Example",
    security_severity: str | None = "high",
    path: str | None = "src/example.py",
    start_line: int | None = 10,
    html_url: str | None = None,
    fixed_at: str | None = None,
    dismissed_at: str | None = None,
) -> dict[str, Any]:
    return {
        "number": number,
        "state": state,
        "rule": {
            "id": rule_id,
            "description": description,
            "security_severity_level": security_severity,
            "severity": "error",
        },
        "most_recent_instance": {
            "ref": "refs/heads/master",
            "location": {
                "path": path,
                "start_line": start_line,
            },
        },
        "html_url": html_url
        or f"https://github.com/example/repo/security/code-scanning/{number}",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "fixed_at": fixed_at,
        "dismissed_at": dismissed_at,
    }


class CompareAlertsTests(unittest.TestCase):
    mod: ModuleType

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_no_change_open_remains_open(self) -> None:
        before = [_alert(1, "open")]
        after = [_alert(1, "open")]
        changes = self.mod.compare_alerts(before, after)
        self.assertEqual(changes["new"], [])
        self.assertEqual(changes["fixed"], [])
        self.assertEqual(changes["reappeared"], [])

    def test_new_alert(self) -> None:
        before: list[dict[str, Any]] = []
        after = [_alert(1, "open")]
        changes = self.mod.compare_alerts(before, after)
        self.assertEqual([a["number"] for a in changes["new"]], [1])
        self.assertEqual(changes["fixed"], [])
        self.assertEqual(changes["reappeared"], [])

    def test_fixed_alert(self) -> None:
        before = [_alert(1, "open")]
        after = [_alert(1, "fixed", fixed_at="2026-01-03T00:00:00Z")]
        changes = self.mod.compare_alerts(before, after)
        self.assertEqual([a["number"] for a in changes["fixed"]], [1])
        self.assertEqual(changes["new"], [])
        self.assertEqual(changes["reappeared"], [])

    def test_dismissed_alert_not_reported_as_fixed(self) -> None:
        before = [_alert(1, "open")]
        after = [_alert(1, "dismissed", dismissed_at="2026-01-03T00:00:00Z")]
        changes = self.mod.compare_alerts(before, after)
        self.assertEqual(changes["fixed"], [])
        self.assertEqual(changes["new"], [])
        self.assertEqual(changes["reappeared"], [])

    def test_multiple_changes_including_reappeared(self) -> None:
        before = [
            _alert(1, "open"),
            _alert(2, "open"),
            _alert(3, "fixed", fixed_at="2026-01-01T00:00:00Z"),
        ]
        after = [
            _alert(1, "fixed", fixed_at="2026-01-03T00:00:00Z"),
            _alert(2, "open"),
            _alert(3, "open"),
            _alert(4, "open"),
        ]
        changes = self.mod.compare_alerts(before, after)
        self.assertEqual([a["number"] for a in changes["fixed"]], [1])
        self.assertEqual([a["number"] for a in changes["reappeared"]], [3])
        self.assertEqual([a["number"] for a in changes["new"]], [4])

    def test_missing_optional_fields_do_not_raise(self) -> None:
        sparse: dict[str, Any] = {
            "number": 9,
            "state": "open",
            "rule": {},
            "most_recent_instance": {},
            "html_url": "https://github.com/example/repo/security/code-scanning/9",
        }
        before: list[dict[str, Any]] = []
        after = [sparse]
        changes = self.mod.compare_alerts(before, after)
        self.assertEqual([a["number"] for a in changes["new"]], [9])
        severity = self.mod.format_severity(sparse)
        self.assertEqual(severity, "UNKNOWN")
        location = self.mod.format_location(sparse)
        self.assertIsInstance(location, str)
        payload = self.mod.build_slack_payload(
            repository="example/repo",
            branch="master",
            changes=changes,
        )
        self.assertIn("blocks", payload)


if __name__ == "__main__":
    unittest.main()
