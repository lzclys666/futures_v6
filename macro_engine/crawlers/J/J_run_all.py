#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_run_all.py
品种: J（焦炭）爬虫总控脚本
调度: 11个因子脚本（8个活跃 + 3个付费因子跳过）
"""
import os
import sys
import datetime
import subprocess
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent / 'common'))
from db_utils import get_pit_dates, ensure_table

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

SCRIPTS = [
    "J_我的钢铁网焦炭现货价格.py",
    "J_焦炭期货收盘价.py",
    "J_焦炭期货仓单.py",
    "J_焦炭期货净持仓.py",
    "J_焦炭期现基差.py",
    "J_焦炭期货近远月价差.py",
    "J_焦炭与焦煤价差.py",
    "J_CCI焦炭价格指数.py",
    "J_钢厂焦炭可用天数.py",
    "J_焦化企业开工率.py",
    "J_焦炭出口FOB价.py",
]

SYMBOL = "J"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--manual', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()
    now = datetime.datetime.now()
    log_file = LOG_DIR / (now.strftime('%Y-%m-%d') + '_' + SYMBOL + '.log')

    print("=" * 50)
    print(f"{SYMBOL} Data Collection @ {now}")
    print(f"PIT: pub={pub_date} obs={obs_date}")
    print(f"Scripts: {len(SCRIPTS)}")
    print("=" * 50)

    success_count = 0
    failures = []

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*50}\n{SYMBOL} start @ {now}\nPIT: pub={pub_date} obs={obs_date}\n{'='*50}\n")

        for script in SCRIPTS:
            script_path = CURRENT_DIR / script
            if not script_path.exists():
                msg = f'[SKIP] not found: {script}'
                print(f"[WARN] {msg}")
                log.write(msg + '\n')
                failures.append((script, 'file_not_found'))
                continue

            print(f">> {script}...")
            log.write(f'--- {script} @ {datetime.datetime.now()} ---\n')

            cmd = [sys.executable, '-X', 'utf8=1', str(script_path)]
            if args.auto:
                cmd.append('--auto')

            try:
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONUTF8'] = '1'

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120,
                    cwd=str(CURRENT_DIR),
                    env=env,
                )

                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(f'[stderr] {result.stderr}\n')

                if result.returncode == 0:
                    success_count += 1
                    print(f"    [OK] {script} done")
                else:
                    print(f"    [WARN] {script} exit:{result.returncode}")
                    failures.append((script, f'exit:{result.returncode}'))

            except subprocess.TimeoutExpired:
                print(f"    [WARN] {script} timeout")
                failures.append((script, 'timeout'))
                log.write(f'[TIMEOUT] {script}\n')
            except Exception as e:
                print(f"    [WARN] {script} exception: {e}")
                failures.append((script, str(e)))
                log.write(f'[EXCEPTION] {script}: {e}\n')

            import time
            time.sleep(1)

        duration = (datetime.datetime.now() - now).total_seconds()
        summary = f"\n{'='*50}\n{SYMBOL} Done  {round(duration,1)}s  {success_count}/{len(SCRIPTS)}\n"
        if failures:
            for n, r in failures:
                summary += f"  - {n}: {r}\n"
        else:
            summary += "[OK] All done\n"
        summary += f"{'='*50}\n"

        log.write(summary)
        print(summary)

if __name__ == "__main__":
    main()
