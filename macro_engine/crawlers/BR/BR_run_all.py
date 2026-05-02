#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BR_run_all.py"""
import os, sys, subprocess, time
from datetime import datetime

# Windows UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    "BR_抓取现货和基差.py",
    "BR_抓取期货持仓.py",
    "BR_抓取库存.py",
    "BR_抓取仓单.py",
    "BR_计算比价.py",
    "BR_批次2_手动输入.py",
]

def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print("[WARN] {} not found".format(name)); return None
    print(">> Running {}...".format(name))
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, path, "--auto"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", errors="replace",
            timeout=60, env=env
        )
        out = (r.stdout or "").strip()
        if out:
            for line in out.splitlines()[-4:]: print("    {}".format(line))
        if r.returncode == 0:
            print("[OK] {} done".format(name)); return True
        else:
            print("[WARN] {} exit code:{}".format(name, r.returncode)); return False
    except Exception as e:
        print("[ERR] {} exception: {}".format(name, e)); return False

def main():
    print("=" * 50)
    print("BR Data Collection @ {}".format(datetime.now()))
    print("Scripts: {}".format(len(SCRIPTS)))
    print("=" * 50)
    t0 = time.time(); ok, fail = 0, 0
    for s in SCRIPTS:
        r = run_script(s)
        if r: ok += 1
        else: fail += 1
        time.sleep(1)
    print("=" * 50)
    print("BR Done  {:.1f}s  {}/{}".format(time.time()-t0, ok, ok+fail))
    print("=" * 50)

if __name__ == "__main__":
    main()
