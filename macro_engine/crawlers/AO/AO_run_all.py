#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_run_all.py - 大连豆一期货数据采集调度脚本
调度顺序: 豆一收盘价 → 豆一持仓量 → 大连期货库存
"""
import subprocess, sys, os, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))
from common.db_utils import ensure_table, get_pit_dates

# 自动模式脚本（免费源）
AUTO_SCRIPTS = [
    'AO_豆一期货收盘价.py',
    'AO_豆一期货持仓量.py',
    'AO_大连期货库存.py',
]

# 手动模式脚本（付费/手动录入）
MANUAL_SCRIPTS = []


def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        return False, f"{name} not found"
    try:
        r = subprocess.run(
            [sys.executable, '-X', 'utf8=1', path, '--auto'],
            capture_output=True, timeout=60
        )
        try:
            out = r.stdout.decode("utf-8", errors="replace")
        except Exception:
            out = str(r.stdout)
        ok = r.returncode == 0
        return ok, out[-200:] if out else ""
    except Exception as e:
        return False, str(e)[:80]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="免费源自动采集")
    parser.add_argument("--manual", action="store_true", help="手动录入脚本")
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sep = "=" * 60
    print(sep)
    print(f"AO Data Collection @ {now}")
    print(f"日期: pub={pub_date} obs={obs_date}")
    print(sep)

    scripts = []
    mode = "unknown"
    if args.auto:
        scripts = AUTO_SCRIPTS
        mode = f"auto - {len(scripts)} 个免费源脚本"
    elif args.manual:
        scripts = MANUAL_SCRIPTS
        mode = f"manual - {len(scripts)} 个付费/手动录入脚本"
    else:
        # 默认auto
        scripts = AUTO_SCRIPTS
        mode = f"auto - {len(scripts)} 个免费源脚本（默认）"

    print(f"[MODE] {mode}")
    print("-" * 60)

    t0 = time.time()
    ok = 0
    for s in scripts:
        print(f">>> {s}...")
        success, detail = run_script(s)
        if detail:
            for line in detail.split('\n'):
                if line.strip():
                    print(f"    {line[:100]}")
        if success:
            print(f"[OK] {s} done")
            ok += 1
        else:
            print(f"[ERR] {s} failed")
    print(sep)
    elapsed = time.time() - t0
    print(f"完成: {ok}/{len(scripts)} 成功, 耗时 {elapsed:.1f}s")
    print(sep)


if __name__ == "__main__":
    main()
