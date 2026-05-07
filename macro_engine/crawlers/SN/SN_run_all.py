#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SN_run_all.py - 沪锡爬虫总控"""
import subprocess, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPT_DIR.parent / 'common'))
from db_utils import get_pit_dates, ensure_table

SCRIPTS = ['SN_沪锡期货收盘价.py', 'SN_沪锡期货持仓量.py', 'SN_沪锡期货库存.py', 'SN_沪锡期货仓单.py', 'SN_沪锡期货净持仓.py', 'SN_沪锡期现基差.py']


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"SN pub={pub_date} obs={obs_date}")
    ok, fail = 0, 0
    for s in SCRIPTS:
        path = SCRIPT_DIR / s
        if not path.exists():
            continue
        print(f">>> {s}")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [sys.executable, '-X', 'utf8=1', str(path)]
        if args.auto:
            cmd.append("--auto")
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             encoding='utf-8', errors='replace', timeout=60,
                             cwd=str(SCRIPT_DIR), env=env)
            out = r.stdout or ""
            for line in out.strip().split('\n')[-2:]:
                if line.strip():
                    print(f"  {line.strip()[:100]}")
            if r.returncode == 0:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  ERR {e}")
            fail += 1
        time.sleep(1)
    print(f"SN Done {ok+fail}/{len(SCRIPTS)} OK={ok} FAIL={fail}")


if __name__ == "__main__":
    main()
