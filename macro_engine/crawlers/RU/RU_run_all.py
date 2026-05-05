#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RU_run_all.py - 天然橡胶爬虫总控
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
    "RU_抓取现货和基差.py",
    "RU_抓取期货持仓.py",
    "RU_期货持仓量.py",
    "RU_抓取库存.py",
    "RU_抓取仓单.py",
    "RU_计算比价.py",
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
    print(f"RU @ {time.strftime('%Y-%m-%d %H:%M:%S')}")
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
                             encoding='utf-8', errors='replace', timeout=120,
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
    print(f"RU Done {ok+fail+skip}/{total}  OK={ok} FAIL={fail} SKIP={skip}")
    print(sep)

    import datetime
    log_file = LOG_DIR / f"{datetime.date.today()}.log"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"RU @ {datetime.datetime.now()} | pub={pub_date} obs={obs_date}\n")
        f.write(f"  OK={ok} FAIL={fail} SKIP={skip}\n")


if __name__ == "__main__":
    main()
