# -*- coding: utf-8 -*-
"""
Alert Manager for futures_v6 trading system.

Provides in-memory + SQLite persistent alert queue with
INFO / WARNING / CRITICAL levels.

Singleton pattern — use get_alert_manager() to obtain the instance.

@author lucy
@date 2026-05-07
"""

import json
import sqlite3
import threading
import logging
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("alert")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALERT_LEVELS = ("INFO", "WARNING", "CRITICAL")
MAX_INMEMORY = 1000
BOOTSTRAP_LOAD = 100

DB_DIR = Path(r"D:\futures_v6\macro_engine")
DB_PATH = DB_DIR / "alerts.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    level       TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    details_json TEXT   NOT NULL DEFAULT '{}'
);
"""

_INSERT_SQL = """
INSERT INTO alerts (timestamp, level, category, message, details_json)
VALUES (?, ?, ?, ?, ?);
"""

_SELECT_RECENT_SQL = """
SELECT id, timestamp, level, category, message, details_json
FROM alerts
ORDER BY id DESC
LIMIT ?;
"""


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------

class AlertManager:
    """In-memory + SQLite alert queue (FIFO, max 1000 in memory)."""

    _instance: Optional["AlertManager"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._queue: deque = deque(maxlen=MAX_INMEMORY)
        self._db_lock = threading.Lock()
        self._init_db()
        self._load_from_db()

    # ---- singleton access ----

    @classmethod
    def get_instance(cls) -> "AlertManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """For testing only — clear the singleton."""
        with cls._lock:
            cls._instance = None

    # ---- DB helpers ----

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_from_db(self) -> None:
        """Load most recent N alerts from SQLite into memory on startup."""
        with self._db_lock:
            try:
                with self._connect() as conn:
                    rows = conn.execute(_SELECT_RECENT_SQL, (BOOTSTRAP_LOAD,)).fetchall()
                # oldest first so deque order matches insertion order
                for row in reversed(rows):
                    self._queue.append(self._row_to_dict(row))
            except Exception as exc:
                logger.warning("Failed to load alerts from DB on startup: %s", exc)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        details = {}
        try:
            details = json.loads(row["details_json"])
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "level": row["level"],
            "category": row["category"],
            "message": row["message"],
            "details": details,
        }

    # ---- public API ----

    def add_alert(
        self,
        level: str,
        category: str,
        message: str,
        details: Optional[dict] = None,
    ) -> dict:
        """
        Add an alert.

        Args:
            level:     INFO | WARNING | CRITICAL
            category:  e.g. 'risk_block', 'risk_warn', 'large_order',
                       'direction_flip', 'high_frequency', 'trade'
            message:   Human-readable description (English only).
            details:   Optional dict stored as JSON.

        Returns:
            The alert dict that was inserted.
        """
        level = level.upper()
        if level not in ALERT_LEVELS:
            level = "INFO"

        ts = datetime.now(timezone.utc).isoformat()
        details = details or {}
        details_json = json.dumps(details, ensure_ascii=False, default=str)

        alert = {
            "timestamp": ts,
            "level": level,
            "category": category,
            "message": message,
            "details": details,
        }

        # write to SQLite first (authoritative)
        with self._db_lock:
            try:
                with self._connect() as conn:
                    cursor = conn.execute(
                        _INSERT_SQL,
                        (ts, level, category, message, details_json),
                    )
                    conn.commit()
                    alert["id"] = cursor.lastrowid
            except Exception as exc:
                logger.error("Failed to persist alert to SQLite: %s", exc)
                alert["id"] = None

        # then in-memory
        self._queue.append(alert)

        return alert

    def get_alerts(
        self,
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> dict:
        """
        Retrieve alerts from the in-memory queue.

        Args:
            level: Optional filter — INFO / WARNING / CRITICAL
            limit: Max items to return (default 100)
            since: ISO timestamp — only return alerts after this time

        Returns:
            {"alerts": [...], "total": N}
        """
        level = level.upper() if level else None

        result = []
        # iterate newest-first (reverse of deque insertion order)
        for alert in reversed(self._queue):
            if level and alert.get("level") != level:
                continue
            if since and alert.get("timestamp", "") <= since:
                continue
            result.append(alert)
            if len(result) >= limit:
                break

        return {"alerts": result, "total": len(result)}

    def get_stats(self) -> dict:
        """Return alert counts by level."""
        counts = {"total": 0, "critical": 0, "warning": 0, "info": 0}
        last_critical: Optional[str] = None

        for alert in self._queue:
            counts["total"] += 1
            lvl = alert.get("level", "").lower()
            if lvl == "critical":
                counts["critical"] += 1
                last_critical = alert.get("timestamp")
            elif lvl == "warning":
                counts["warning"] += 1
            elif lvl == "info":
                counts["info"] += 1

        return {
            "total": counts["total"],
            "critical": counts["critical"],
            "warning": counts["warning"],
            "info": counts["info"],
            "last_critical": last_critical,
        }


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def get_alert_manager() -> AlertManager:
    """Module-level accessor — same as AlertManager.get_instance()."""
    return AlertManager.get_instance()
