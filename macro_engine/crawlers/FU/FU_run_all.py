#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_run_all.py
"""
import os, sys, subprocess, time, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import ensure_table, get_pit_dates

# Windows UTF-8 编码修复
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    "FU_WTI收盘价.py",
    "FU_抓取仓单.py",
    "FU_抓取期货持仓.py",
    "FU_抓取现货和基差.py",
    "FU_新加坡库存.py",
    "FU_高低硫价差.py",
]


def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print("[WARN] {} not found".format(name))
        return None
    print(">> 运行 {}...".format(name))
    try:
        r = subprocess.run([sys.executable, path, "--auto"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120)
        out = (r.stdout or "").strip()
        if out:
            for line in out.splitlines()[-4:]:
                print("    {}".format(line))
        if r.returncode == 0:
            print("[OK] {} done".format(name))
            return True
        else:
            print("[WARN] {} exit:{}".format(name, r.returncode))
            return False
    except Exception as e:
        print("[ERR] {} exception: {}".format(name, e))
        return False


def main():
    print("=" * 50)
    print("开始执行 FU 数据采集 @ {}".format(datetime.now()))
    print("待执行脚本数: {}".format(len(SCRIPTS)))
    print("=" * 50)
    t0 = time.time()
    ok, fail = 0, 0
    for s in SCRIPTS:
        r = run_script(s)
        if r:
            ok += 1
        else:
            fail += 1
        time.sleep(1)
    print("=" * 50)
    print("FU 数据采集完成  耗时:{:.1f}s  成功:{}/{}".format(time.time() - t0, ok, ok + fail))
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true', help='自动模式')
    parser.add_argument('--manual', action='store_true', help='手动模式')
    args = parser.parse_args()
    ensure_table()
    main()
