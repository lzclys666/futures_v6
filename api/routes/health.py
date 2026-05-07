#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced health check route for macro-api.

Provides structured health checks:
  - Database connection (pit_data.db)
  - SignalBridge status (CSV readability)
  - Last daily_scoring timestamp
  - Disk space (output/ directory)

Returns: {"status": "ok"|"degraded"|"down", "service": "macro-api", "version": "1.0.0", "checks": {...}}
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger("macro_api.health")

router = APIRouter()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "macro_engine" / "pit_data.db"
_OUTPUT_DIR = _PROJECT_ROOT / "macro_engine" / "output"

# Allow override via environment variables
if os.environ.get("HEALTH_DB_PATH"):
    _DB_PATH = Path(os.environ["HEALTH_DB_PATH"])
if os.environ.get("HEALTH_OUTPUT_DIR"):
    _OUTPUT_DIR = Path(os.environ["HEALTH_OUTPUT_DIR"])

# Scoring staleness threshold (hours) — if last scoring is older than this, mark degraded
_SCORING_STALE_HOURS = 48


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------
def _check_database() -> Dict[str, Any]:
    """Check pit_data.db connectivity and basic integrity."""
    result: Dict[str, Any] = {"status": "ok"}
    try:
        if not _DB_PATH.exists():
            result["status"] = "down"
            result["detail"] = f"Database file not found: {_DB_PATH}"
            return result

        conn = sqlite3.connect(str(_DB_PATH), timeout=5)
        try:
            cur = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cur.fetchone()[0]
            conn.execute("SELECT 1")
            result["table_count"] = table_count
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        result["status"] = "down"
        result["detail"] = f"Database error: {e}"
    except Exception as e:
        result["status"] = "down"
        result["detail"] = f"Unexpected: {e}"
    return result


def _check_signal_bridge() -> Dict[str, Any]:
    """Check SignalBridge — can we read the latest CSV files?"""
    result: Dict[str, Any] = {"status": "ok"}
    try:
        if not _OUTPUT_DIR.exists():
            result["status"] = "down"
            result["detail"] = f"Output directory not found: {_OUTPUT_DIR}"
            return result

        # Check that at least one today's CSV exists
        today_str = datetime.now().strftime("%Y%m%d")
        today_csvs = list(_OUTPUT_DIR.glob(f"*_macro_daily_{today_str}.csv"))
        if today_csvs:
            result["today_csv_count"] = len(today_csvs)
            # Try reading the first one
            try:
                with open(today_csvs[0], "r", encoding="utf-8-sig") as f:
                    first_line = f.readline()
                result["csv_readable"] = True
            except Exception as e:
                result["status"] = "degraded"
                result["detail"] = f"CSV read error: {e}"
                result["csv_readable"] = False
        else:
            # No today CSV — check if any recent CSVs exist (within 3 days)
            recent_csvs = [
                f for f in _OUTPUT_DIR.glob("*_macro_daily_*.csv")
                if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() < 3 * 86400
            ]
            if recent_csvs:
                result["status"] = "degraded"
                result["detail"] = "No CSV for today, but recent CSVs exist"
                result["recent_csv_count"] = len(recent_csvs)
            else:
                result["status"] = "down"
                result["detail"] = "No recent CSV files found"

        # Check SignalBridge global instance
        try:
            from services.signal_bridge import get_signal_bridge
            bridge = get_signal_bridge()
            if bridge is not None:
                cached = bridge.get_all_signals()
                result["cached_symbols"] = list(cached.keys())
                result["bridge_active"] = True
            else:
                result["bridge_active"] = False
                if result["status"] == "ok":
                    result["status"] = "degraded"
                    result["detail"] = "SignalBridge not initialized"
        except ImportError:
            result["bridge_active"] = False
            if result["status"] == "ok":
                result["status"] = "degraded"
                result["detail"] = "SignalBridge import failed"

    except Exception as e:
        result["status"] = "down"
        result["detail"] = f"Unexpected: {e}"
    return result


def _check_last_scoring() -> Dict[str, Any]:
    """Check when the last daily scoring ran — by looking at CSV modification times."""
    result: Dict[str, Any] = {"status": "ok"}
    try:
        if not _OUTPUT_DIR.exists():
            result["status"] = "down"
            result["last_scoring"] = None
            result["detail"] = "Output directory not found"
            return result

        # Find the most recently modified CSV
        latest_time: float = 0.0
        latest_file: str = ""
        for f in _OUTPUT_DIR.glob("*_macro_daily_*.csv"):
            try:
                mtime = f.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = f.name
            except OSError:
                continue

        if latest_time == 0.0:
            result["status"] = "down"
            result["last_scoring"] = None
            result["detail"] = "No CSV files found"
            return result

        last_dt = datetime.fromtimestamp(latest_time)
        result["last_scoring"] = last_dt.isoformat()
        result["latest_file"] = latest_file

        hours_since = (datetime.now() - last_dt).total_seconds() / 3600
        result["hours_since_scoring"] = round(hours_since, 1)

        if hours_since > _SCORING_STALE_HOURS:
            result["status"] = "degraded"
            result["detail"] = f"Last scoring {hours_since:.1f}h ago (stale > {_SCORING_STALE_HOURS}h)"

    except Exception as e:
        result["status"] = "down"
        result["last_scoring"] = None
        result["detail"] = f"Unexpected: {e}"
    return result


def _check_disk_space() -> Dict[str, Any]:
    """Check available disk space for the output directory."""
    result: Dict[str, Any] = {"status": "ok"}
    try:
        usage = shutil.disk_usage(str(_OUTPUT_DIR))
        free_mb = usage.free // (1024 * 1024)
        total_mb = usage.total // (1024 * 1024)
        used_pct = round(usage.used / usage.total * 100, 1) if usage.total > 0 else 0

        result["free_mb"] = free_mb
        result["total_mb"] = total_mb
        result["used_pct"] = used_pct

        # Degraded if < 1GB free, down if < 100MB
        if free_mb < 100:
            result["status"] = "down"
            result["detail"] = f"Critical: only {free_mb}MB free"
        elif free_mb < 1024:
            result["status"] = "degraded"
            result["detail"] = f"Low disk: {free_mb}MB free"
    except Exception as e:
        result["status"] = "down"
        result["detail"] = f"Unexpected: {e}"
        result["free_mb"] = None
    return result


# ---------------------------------------------------------------------------
# Aggregate health
# ---------------------------------------------------------------------------
def _aggregate_status(checks: Dict[str, Dict[str, Any]]) -> str:
    """Determine overall status from individual check results."""
    statuses = [c.get("status", "ok") for c in checks.values()]
    if any(s == "down" for s in statuses):
        return "down"
    if any(s == "degraded" for s in statuses):
        return "degraded"
    return "ok"


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
@router.get("/health", tags=["system"])
def health_enhanced():
    """
    Enhanced health check endpoint.

    Returns:
    - status: "ok" | "degraded" | "down"
    - checks: individual check results
    """
    checks = {
        "database": _check_database(),
        "signal_bridge": _check_signal_bridge(),
        "last_scoring": _check_last_scoring(),
        "disk_space": _check_disk_space(),
    }

    # Flatten disk_space.free_mb to top level for convenience
    overall = _aggregate_status(checks)

    response = {
        "status": overall,
        "service": "macro-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }

    # Also expose key metrics at top level for quick scanning
    if checks["disk_space"].get("free_mb") is not None:
        response["disk_space_mb"] = checks["disk_space"]["free_mb"]
    if checks["last_scoring"].get("last_scoring"):
        response["last_scoring"] = checks["last_scoring"]["last_scoring"]

    return response
