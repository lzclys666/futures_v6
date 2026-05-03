#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AL_run_all.py - 沪铝爬虫总控"""
import os, sys, subprocess, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

scripts = [
    # [SKIP]永久跳过: AL_抓取上期所沪铝仓单.py (SHFE API 404)
    # [SKIP]永久跳过: AL_计算期现基差.py (无免费铝现货价)
    "AL_抓取LME铝库存.py",
    "AL_抓取LME铝价_铝道网.py",
    "AL_抓取净持仓.py",
    "AL_计算持仓集中度.py",
    "AL_计算近远月价差.py",
    "AL_计算SHFE_LME比价.py",
    "AL_计算铝铜比价.py",
]

def run_all():
    now = datetime.datetime.now()
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}.log"

    print("=" * 50)
    print(f"AL Data Collection @ {now}")
    print(f"Scripts: {len(scripts)}")
    print("=" * 50)

    success_count = 0
    failures = []

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*50}\nAL Start @ {now}\n{'='*50}\n")

        for script in scripts:
            script_path = CURRENT_DIR / script
            if not script_path.exists():
                msg = f"[SKIP] {script} not found"
                print(msg)
                log.write(f"{msg}\n")
                failures.append((script, "not found"))
                continue

            print(f">>> {script}...")
            log.write(f"\n--- {script} @ {datetime.datetime.now()} ---\n")

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            try:
                result = subprocess.run(
                    [sys.executable, str(script_path), "--auto"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120,
                    cwd=str(CURRENT_DIR),
                    env=env
                )

                log.write(result.stdout if result.stdout else "")
                if result.stderr:
                    log.write(f"[stderr] {result.stderr}\n")

                if result.returncode == 0:
                    success_count += 1
                    print(f"[OK] {script} done")
                else:
                    print(f"[WARN] {script} exit:{result.returncode}")
                    failures.append((script, f"exit {result.returncode}"))

            except subprocess.TimeoutExpired:
                msg = f"{script} TIMEOUT (>120s)"
                print(f"[WARN] {msg}")
                failures.append((script, "timeout"))

            except Exception as e:
                msg = f"{script} exception: {e}"
                print(f"[ERR] {msg}")
                failures.append((script, str(e)))

        duration = (datetime.datetime.now() - now).total_seconds()
        print(f"\n{'='*50}")
        print(f"AL Done  {duration:.1f}s  Success:{success_count}/{len(scripts)}")
        if failures:
            print(f"Failures:")
            for name, reason in failures:
                print(f"  - {name}: {reason}")
        else:
            print("[OK] All done")
        print(f"{'='*50}")

        log.write(f"\n[Done] {success_count}/{len(scripts)}\n")

if __name__ == "__main__":
    run_all()
