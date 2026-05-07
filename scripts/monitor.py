# -*- coding: utf-8 -*-
"""
Service health monitor for futures_v6.

Periodically checks /health endpoint and logs status.
Exits with code 0=healthy, 1=degraded, 2=unavailable.

Usage:
    python scripts/monitor.py --interval 60 --fail-threshold 3 --port 8000

@date 2026-05-07
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "monitor.log"


def check_health(port: int, timeout: int = 10) -> dict:
    """Call /health endpoint and return result dict."""
    url = f"http://localhost:{port}/health"
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"status": "ok", "data": data, "code": resp.status}
    except URLError as e:
        return {"status": "unavailable", "error": str(e), "code": 0}
    except Exception as e:
        return {"status": "error", "error": str(e), "code": 0}


def write_log(message: str) -> None:
    """Append to monitor log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().isoformat()
    line = f"[{ts}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.rstrip())


def main():
    parser = argparse.ArgumentParser(description="futures_v6 service health monitor")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    parser.add_argument("--fail-threshold", type=int, default=3, help="Consecutive failures before alerting")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument("--once", action="store_true", help="Check once and exit")
    args = parser.parse_args()

    consecutive_failures = 0
    exit_code = 0

    while True:
        result = check_health(args.port)
        status = result.get("status", "unknown")

        if status == "ok":
            health_data = result.get("data", {})
            overall = health_data.get("status", "unknown")
            checks = health_data.get("checks", {})

            if overall == "ok":
                write_log(f"HEALTHY - {json.dumps(checks)}")
                consecutive_failures = 0
                exit_code = 0
            elif overall == "degraded":
                write_log(f"DEGRADED - {json.dumps(checks)}")
                consecutive_failures = 0
                exit_code = 1
            else:
                write_log(f"UNHEALTHY - status={overall}")
                consecutive_failures += 1
                exit_code = 2
        else:
            error = result.get("error", "unknown error")
            consecutive_failures += 1
            write_log(f"UNAVAILABLE (fail {consecutive_failures}/{args.fail_threshold}) - {error}")
            exit_code = 2

        if consecutive_failures >= args.fail_threshold:
            write_log(f"ALERT: {consecutive_failures} consecutive failures! Service may be down.")

        if args.once:
            sys.exit(exit_code)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
