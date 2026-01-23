"""
Issue Logger (TypeF Hardening)

Goal:
- When errors happen repeatedly, track them as an "open issue"
- Once fixed (i.e., stops happening), close the issue automatically
- Write structured JSONL logs for audit

Files created:
- prototype/outputs/issue_log_open.jsonl
- prototype/outputs/issue_log_closed.jsonl
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


class IssueLogger:
    """
    Tracks runtime issues and closes them when issue disappears.

    Usage:
        issue = IssueLogger(out_dir="prototype/outputs")

        # on error
        issue.track_runtime_error("E_X", "Title", details={...})

        # optionally call regularly for "health ok" -> auto close
        issue.mark_healthy()
    """

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        ensure_dir(self.out_dir)

        self.open_path = os.path.join(self.out_dir, "issue_log_open.jsonl")
        self.closed_path = os.path.join(self.out_dir, "issue_log_closed.jsonl")

        # issue_key -> state
        self._open: Dict[str, Dict[str, Any]] = {}

        # if an issue stops appearing for N cycles -> auto close
        self._close_after_ok_ticks = 3

    def _write(self, path: str, rec: Dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _open_issue(self, issue_key: str, title: str, details: Dict[str, Any]) -> None:
        self._open[issue_key] = {
            "issue_key": issue_key,
            "title": title,
            "opened_at": utc_now_iso(),
            "last_seen_at": utc_now_iso(),
            "count": 1,
            "ok_ticks": 0,
            "details": details,
        }
        self._write(self.open_path, {
            "ts": utc_now_iso(),
            "event": "ISSUE_OPEN",
            "issue_key": issue_key,
            "title": title,
            "details": details,
        })

    def _touch_issue(self, issue_key: str, details: Dict[str, Any]) -> None:
        st = self._open[issue_key]
        st["last_seen_at"] = utc_now_iso()
        st["count"] += 1
        st["ok_ticks"] = 0
        st["details"] = details

        self._write(self.open_path, {
            "ts": utc_now_iso(),
            "event": "ISSUE_SEEN",
            "issue_key": issue_key,
            "count": st["count"],
            "details": details,
        })

    def _close_issue(self, issue_key: str, reason: str = "AUTO_CLOSED") -> None:
        st = self._open.get(issue_key)
        if not st:
            return

        rec = {
            "ts": utc_now_iso(),
            "event": "ISSUE_CLOSED",
            "issue_key": issue_key,
            "title": st.get("title"),
            "opened_at": st.get("opened_at"),
            "closed_at": utc_now_iso(),
            "count": st.get("count"),
            "reason": reason,
            "last_details": st.get("details"),
        }
        self._write(self.closed_path, rec)
        del self._open[issue_key]

    def track_runtime_error(self, issue_key: str, title: str, details: Dict[str, Any]) -> None:
        """
        Call this whenever runtime errors occur.
        It opens issue if not opened, or increments it.
        """
        if issue_key not in self._open:
            self._open_issue(issue_key, title, details)
        else:
            self._touch_issue(issue_key, details)

    def mark_healthy(self) -> None:
        """
        Call this when one successful loop occurs with no error.
        After N ok ticks, the issue auto closes.
        """
        keys = list(self._open.keys())
        for k in keys:
            self._open[k]["ok_ticks"] += 1
            if self._open[k]["ok_ticks"] >= self._close_after_ok_ticks:
                self._close_issue(k, reason="AUTO_CLOSED_AFTER_OK_TICKS")
