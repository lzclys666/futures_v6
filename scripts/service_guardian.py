"""
Service Guardian - API 服务守护进程
===================================
监控 API 服务（FastAPI on port 8000）健康状态，崩溃后自动重启。

功能：
  - 启动 API 服务子进程
  - 定期 HTTP 健康检查（默认 30s 间隔）
  - 连续 3 次失败后自动重启子进程
  - 最大重启次数限制（防无限循环，默认 10 次）
  - 端口冲突检测
  - 优雅关闭（SIGTERM/SIGINT → 清理子进程）
  - 日志写入 logs/guardian.log

用法：
  python service_guardian.py [--port 8000] [--max-restarts 10] [--check-interval 30]

零外部依赖，仅使用 Python 标准库。
"""

import argparse
import logging
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(r"D:\futures_v6")
START_SCRIPT = PROJECT_ROOT / "_start_server.py"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "guardian.log"

MAX_CONSECUTIVE_FAILURES = 3
HEALTH_CHECK_TIMEOUT = 5  # seconds


# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configure dual logging: file + console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("guardian")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler (UTF-8 for Chinese)
    fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# ---------------------------------------------------------------------------
# Port Check
# ---------------------------------------------------------------------------

def is_port_in_use(port: int) -> bool:
    """Check if a TCP port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

def check_health(port: int) -> bool:
    """
    HTTP GET /health endpoint. Returns True if healthy.
    Expected response: {"status": "ok", ...}
    """
    url = f"http://127.0.0.1:{port}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=HEALTH_CHECK_TIMEOUT) as resp:
            if resp.status == 200:
                import json
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("status") == "ok"
        return False
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return False


# ---------------------------------------------------------------------------
# Guardian
# ---------------------------------------------------------------------------

class ServiceGuardian:
    """Monitors and auto-restarts the API service."""

    def __init__(self, port: int, max_restarts: int, check_interval: int):
        self.port = port
        self.max_restarts = max_restarts
        self.check_interval = check_interval
        self.process: subprocess.Popen | None = None
        self.restart_count = 0
        self.running = True
        self.logger = logging.getLogger("guardian")

    def start_service(self) -> bool:
        """Start the API service as a subprocess."""
        if not START_SCRIPT.exists():
            self.logger.error(f"Start script not found: {START_SCRIPT}")
            return False

        # Port conflict check
        if is_port_in_use(self.port):
            self.logger.warning(
                f"Port {self.port} is already in use. "
                "Waiting 5s for it to free up..."
            )
            time.sleep(5)
            if is_port_in_use(self.port):
                self.logger.error(
                    f"Port {self.port} still in use. Cannot start service."
                )
                return False

        try:
            self.logger.info(
                f"Starting API service (restart #{self.restart_count})..."
            )
            self.process = subprocess.Popen(
                [sys.executable, str(START_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            # Give it time to initialize
            time.sleep(5)

            if self.process.poll() is not None:
                self.logger.error(
                    f"Service exited immediately with code {self.process.returncode}"
                )
                return False

            self.logger.info(
                f"Service started (PID: {self.process.pid})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False

    def stop_service(self):
        """Gracefully stop the service subprocess."""
        if self.process is None:
            return
        if self.process.poll() is not None:
            self.process = None
            return

        pid = self.process.pid
        self.logger.info(f"Stopping service (PID: {pid})...")

        try:
            # Windows: send CTRL_BREAK to the process group
            if sys.platform == "win32":
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.process.terminate()

            # Wait up to 10s for graceful shutdown
            try:
                self.process.wait(timeout=10)
                self.logger.info(f"Service stopped gracefully (PID: {pid})")
            except subprocess.TimeoutExpired:
                self.logger.warning(
                    f"Service did not stop in 10s, force killing (PID: {pid})"
                )
                self.process.kill()
                self.process.wait(timeout=5)
        except Exception as e:
            self.logger.error(f"Error stopping service: {e}")
            try:
                self.process.kill()
            except Exception:
                pass
        finally:
            self.process = None

    def restart_service(self):
        """Stop and restart the service."""
        self.restart_count += 1
        self.logger.warning(
            f"Restarting service ({self.restart_count}/{self.max_restarts})..."
        )
        self.stop_service()
        # Brief cooldown before restart
        time.sleep(3)
        return self.start_service()

    def run(self):
        """Main guardian loop."""
        self.logger.info("=" * 60)
        self.logger.info("Service Guardian started")
        self.logger.info(f"  Port: {self.port}")
        self.logger.info(f"  Max restarts: {self.max_restarts}")
        self.logger.info(f"  Check interval: {self.check_interval}s")
        self.logger.info(f"  Script: {START_SCRIPT}")
        self.logger.info("=" * 60)

        # Initial start
        if not self.start_service():
            self.logger.error("Initial service start failed. Exiting.")
            return 1

        consecutive_failures = 0

        while self.running:
            time.sleep(self.check_interval)

            if not self.running:
                break

            # Check if process is still alive
            if self.process and self.process.poll() is not None:
                exit_code = self.process.returncode
                self.logger.warning(
                    f"Service process exited unexpectedly (code: {exit_code})"
                )
                consecutive_failures = MAX_CONSECUTIVE_FAILURES  # immediate restart
            elif check_health(self.port):
                if consecutive_failures > 0:
                    self.logger.info("Health check recovered.")
                consecutive_failures = 0
                continue
            else:
                consecutive_failures += 1
                self.logger.warning(
                    f"Health check failed ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})"
                )

            # Trigger restart after consecutive failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                if self.restart_count >= self.max_restarts:
                    self.logger.error(
                        f"Max restarts ({self.max_restarts}) reached. "
                        "Guardian giving up."
                    )
                    self.stop_service()
                    return 1

                if not self.restart_service():
                    self.logger.error("Restart failed.")
                    if self.restart_count >= self.max_restarts:
                        return 1
                consecutive_failures = 0

        self.logger.info("Guardian stopped.")
        return 0

    def shutdown(self):
        """Signal handler: graceful shutdown."""
        self.logger.info("Shutdown signal received.")
        self.running = False
        self.stop_service()


# ---------------------------------------------------------------------------
# Signal Handling
# ---------------------------------------------------------------------------

_guardian: ServiceGuardian | None = None


def _signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _guardian
    if _guardian:
        _guardian.shutdown()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _guardian

    parser = argparse.ArgumentParser(
        description="API Service Guardian - auto-restart on crash"
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Health check port (default: 8000)"
    )
    parser.add_argument(
        "--max-restarts", type=int, default=10,
        help="Maximum restart attempts (default: 10)"
    )
    parser.add_argument(
        "--check-interval", type=int, default=30,
        help="Health check interval in seconds (default: 30)"
    )
    args = parser.parse_args()

    setup_logging()

    _guardian = ServiceGuardian(
        port=args.port,
        max_restarts=args.max_restarts,
        check_interval=args.check_interval,
    )

    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    return _guardian.run()


if __name__ == "__main__":
    sys.exit(main())
