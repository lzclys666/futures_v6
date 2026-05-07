#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I_run_all.py - 铁矿石数据采集（subprocess模式）"""
import os, sys, subprocess, datetime, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import get_pit_dates, ensure_table

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

auto_scripts = [
    "I_抓取期货收盘价.py",
    "I_抓取港口库存.py",
    "I_抓取期货持仓量.py",
    "I_铁矿石现货价.py",
    "I_铁矿石期货仓单.py",
    "I_计算基差.py",
    "I_计算近远月价差.py",
    "I_铁矿石港口库存变化.py",
    "I_铁矿螺纹比价.py",
]

manual_scripts = [
    "I_批次2_手动输入.py",
    "I_铁矿石期货净持仓.py",  # [BLOCKED] DCE反爬，等待AKShare修复
]

all_scripts = auto_scripts + manual_scripts

def run_all(scripts):
    now = datetime.datetime.now()
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}_I.log"

    print("=" * 50)
    print(f"I Data Collection @ {now}")
    print(f"PIT: pub={pub_date} obs={obs_date}")
    print(f"Scripts: {len(scripts)}")
    print("=" * 50)

    success_count = 0
    failures = []

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*50}\nI Start @ {now}\n{'='*50}\n")

        for script in scripts:
            script_path = CURRENT_DIR / script
            if not script_path.exists():
                msg = f"[SKIP] {script} not found"
                print(msg); log.write(f"{msg}\n")
                failures.append((script, "not found"))
                continue

            print(f">> {script}...")
            log.write(f"\n--- {script} @ {datetime.datetime.now()} ---\n")

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            try:
                result = subprocess.run(
                    [sys.executable, "-X", "utf8=1", str(script_path), "--auto"],
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
                    print(f"    [OK] {script} done")
                else:
                    print(f"    [WARN] {script} exit:{result.returncode}")
                    failures.append((script, f"exit {result.returncode}"))

            except subprocess.TimeoutExpired:
                msg = f"{script} TIMEOUT"
                print(f"    [WARN] {msg}")
                failures.append((script, "timeout"))
            except Exception as e:
                msg = f"{script} exception: {e}"
                print(f"    [ERR] {msg}")
                failures.append((script, str(e)))

        duration = (datetime.datetime.now() - now).total_seconds()
        print(f"\n{'='*50}")
        print(f"I Done  {duration:.1f}s  {success_count}/{len(scripts)}")
        if failures:
            for n, r in failures:
                print(f"  - {n}: {r}")
        else:
            print("[OK] All done")
        print(f"{'='*50}")
        log.write(f"\n[Done] {success_count}/{len(scripts)}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true', help='只跑免费源脚本')
    parser.add_argument('--manual', action='store_true', help='只跑付费源/兜底脚本')
    args = parser.parse_args()

    if args.manual:
        scripts = manual_scripts
    elif args.auto:
        scripts = auto_scripts
    else:
        scripts = all_scripts

    run_all(scripts)
