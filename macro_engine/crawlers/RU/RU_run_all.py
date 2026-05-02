#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RU_run_all.py"""
import os, sys, subprocess, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    "RU_抓取现货和基差.py",
    "RU_抓取期货持仓.py",
    "RU_期货持仓量.py",
    "RU_抓取库存.py",
    "RU_抓取仓单.py",
    "RU_计算比价.py",
]

def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print("[WARN] {} not found".format(name)); return None
    print(">> running {}...".format(name))
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, path, "--auto"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, env=env)
        out = (r.stdout or "").strip()
        if out:
            for line in out.splitlines()[-4:]: print("    " + line)
        if r.returncode == 0:
            print("[OK] {} done".format(name)); return True
        else:
            print("[WARN] {} exit:{}".format(name, r.returncode)); return False
    except Exception as e:
        print("[ERR] {} except:{}".format(name, e)); return False

def main():
    print("=" * 50)
    print("RU采集 start @ " + str(datetime.now()))
    print("待执行: " + str(len(SCRIPTS)) + " scripts")
    print("=" * 50)
    t0 = time.time(); ok, fail = 0, 0
    for s in SCRIPTS:
        r = run_script(s)
        if r: ok += 1
        else: fail += 1
        time.sleep(1)
    print("=" * 50)
    print("RU done  {:.1f}s  OK:{}/{}".format(time.time()-t0, ok, ok+fail))
    print("=" * 50)

if __name__ == "__main__":
    main()
