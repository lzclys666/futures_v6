#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P_run_all.py - 棕榈油日度数据采集总调度
批次1: 免费数据源 (AKShare DCE/INE) - 5个因子
批次2: MPOB月报PDF解析/进口量海关总署 (付费/需解析)
"""
import subprocess, sys, os, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    "P_抓取期货收盘价.py",     # P_FUT_CLOSE
    "P_抓取期货持仓量.py",     # P_FUT_OI
    "P_原油参考.py",          # P_OIL_REF
    "P_计算基差.py",          # P_SPD_BASIS (可能滞后)
    "P_计算近远月价差.py",    # P_SPD_CONTRACT (可能滞后)
    # P_批次2_手动输入.py,  # 批次2付费因子
]

BATCH2 = [
    # "P_批次2_手动输入.py",
]

def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print("? %s does not exist" % name)
        return False
    print(">> %s" % name)
    try:
        r = subprocess.run(
            [sys.executable, path, "--auto"],
            capture_output=True, timeout=30
        )
        try:
            out = r.stdout.decode('utf-8', errors='replace')
        except (ValueError, IndexError):
            out = str(r.stdout)
        for line in out.strip().split('\r\n')[-3:]:
            if line.strip():
                try:
                    print("   %s" % line[:120])
                except (ValueError, IndexError):
                    pass
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print("   TIMEOUT")
        return False
    except Exception as e:
        print("   Exception: %s" % str(e)[:80])
        return False

def main():
    print("=" * 50)
    print("P(棕榈油) @ %s" % datetime.now())
    print("=" * 50)
    t0 = time.time()
    ok, fail = 0, 0
    for s in SCRIPTS:
        if run_script(s):
            ok += 1
        else:
            fail += 1
        time.sleep(0.5)
    print("=" * 50)
    print("P Done  %.1fs  OK=%d FAIL=%d" % (time.time()-t0, ok, fail))
    print("=" * 50)

if __name__ == "__main__":
    main()
