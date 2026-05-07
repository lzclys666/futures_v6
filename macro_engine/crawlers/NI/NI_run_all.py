#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NI_run_all.py - 镍爬虫总控
"""
import subprocess, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPT_DIR.parent / 'common'))
from db_utils import get_pit_dates, ensure_table

SCRIPTS = [
    "NI_抓取期货收盘价.py",
    "NI_抓取期货持仓量.py",
    "NI_沪镍期货库存.py",
    "NI_计算基差.py",
    "NI_抓取SHFE仓单.py",
    "NI_抓取持仓排名.py",
]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--manual", action="store_true")
    args = parser.parse_args()

    pub_date, obs_date = get_pit_dates()
    ensure_table()

    sep = "=" * 50
    print(sep)
    print(f"NI @ {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"pub_date={pub_date} obs_date={obs_date}")
    print(sep)

    ok, fail, skip = 0, 0, 0
    for s in SCRIPTS:
        path = SCRIPT_DIR / s
        if not path.exists():
            print(f"  [跳过] {s} 不存在")
            skip += 1
            continue

        print(f"\n>>> {s}...")
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
            for line in out.strip().split('\n')[-3:]:
                if line.strip():
                    print(f"  {line.strip()[:120]}")
            if r.returncode == 0:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  [异常] {e}")
            fail += 1
        time.sleep(1)

    print(sep)
    total = ok + fail + skip
    print(f"NI Done {ok+fail+skip}/{total}  OK={ok} FAIL={fail} SKIP={skip}")
    print(sep)

    import datetime
    log_file = LOG_DIR / f"{datetime.date.today()}.log"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"NI @ {datetime.datetime.now()} | pub={pub_date} obs={obs_date}\n")
        f.write(f"  OK={ok} FAIL={fail} SKIP={skip}\n")


if __name__ == "__main__":
    main()
