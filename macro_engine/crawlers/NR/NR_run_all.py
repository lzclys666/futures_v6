#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NR_run_all.py"""
import os, sys, subprocess, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    "NR_抓取橡胶.py",  # NR_INV_TOTAL
    "NR_抓取BDI.py",  # NR_FREIGHT_BDI
    "NR_抓取仓单.py",  # NR_STK_WARRANT
    "NR_抓取持仓排名.py",  # NR_POS_NET
    "NR_抓取期货持仓.py",  # NR_FUT_OI
    "NR_计算RU-NR价差.py",  # NR_SPD_RU_NR
    "NR_天然橡胶期货收盘价.py",  # NR_FUT_CLOSE
    "NR_橡胶持仓量.py",  # NR_POS_OPEN_INT
    "NR_橡胶合约间价差.py",  # NR_SPD_CONTRACT
    "NR_抓取现货和基差.py",  # NR_SPD_BASIS
    "NR_批次2_手动输入.py",  # batch2
]

def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print("[WARN] {} not found".format(name)); return None
    print(">> Running {}...".format(name))
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, path, "--auto"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
        out = (r.stdout or "").strip()
        if out:
            for line in out.splitlines()[-4:]: print("    {}".format(line))
        if r.returncode == 0:
            print("[OK] {} complete".format(name)); return True
        else:
            print("[WARN] {} error code:{}".format(name, r.returncode)); return False
    except Exception as e:
        print("[FAIL] {} exception: {}".format(name, e)); return False

def main():
    print("=" * 50)
    print("NR Data Collection @ {}".format(datetime.now()))
    print("Scripts to run: {}".format(len(SCRIPTS)))
    print("=" * 50)
    t0 = time.time(); ok, fail = 0, 0
    for s in SCRIPTS:
        r = run_script(s)
        if r: ok += 1
        else: fail += 1
        time.sleep(0.5)
    print("=" * 50)
    print("NR Data Collection Done  {:.1f}s  Success:{}/{}".format(time.time()-t0, ok, ok+fail))
    print("=" * 50)

if __name__ == "__main__":
    main()
