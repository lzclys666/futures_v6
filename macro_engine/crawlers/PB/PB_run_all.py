#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_run_all.py - 铅爬虫总控
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
    'PB_沪铅期货收盘价.py',
    'PB_沪铅期货持仓量.py',
    'PB_沪铅现货价.py',
    'PB_SMM沪铅现货价格.py',
    'PB_沪铅期现基差.py',
    'PB_沪铅期货近远月价差.py',
    'PB_沪铅期货净持仓.py',
    'PB_铅锭仓单库存.py',
    'PB_期货交易所铅库存.py',
    'PB_铅锭社会库存.py',
    'PB_铅酸电池用铅占比.py',
    'PB_美元兑人民币汇率.py',
    'PB_原生铅产能利用率.py',
    'PB_铅TC加工费.py',
    'PB_原生铅与再生铅价差.py',
    'PB_铅锭社会库存_东方.py',
    'PB_铅锭产量.py',
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
    print(f"PB @ {time.strftime('%Y-%m-%d %H:%M:%S')}")
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
    print(f"PB Done {ok+fail+skip}/{total}  OK={ok} FAIL={fail} SKIP={skip}")
    print(sep)


if __name__ == "__main__":
    main()
