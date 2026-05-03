#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys, os, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    "NI_抓取期货收盘价.py",
    "NI_抓取期货持仓量.py",
    "NI_计算基差.py",
    "NI_抓取SHFE仓单.py",
    "../CU_NI/CU_NI_LME升贴水.py",
]

def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print("? %s" % name)
        return False
    print(">> %s" % name)
    try:
        r = subprocess.run([sys.executable, path, "--auto"], capture_output=True, timeout=30)
        try:
            out = r.stdout.decode("utf-8", errors="replace")
        except (ValueError, IndexError):
            out = str(r.stdout)
        for line in out.strip().split("\r\n")[-3:]:
            if line.strip():
                try:
                    print("   %s" % line[:120])
                except (ValueError, IndexError):
                    pass
        return r.returncode == 0
    except Exception as e:
        print("   Exception: %s" % str(e)[:80])
        return False

def main():
    print("=" * 50)
    print("NI @ %s" % datetime.now())
    print("=" * 50)
    t0 = time.time()
    ok = sum(1 for s in SCRIPTS if run_script(s))
    print("=" * 50)
    print("NI Done %.1fs OK=%d/%d" % (time.time()-t0, ok, len(SCRIPTS)))
    print("=" * 50)

if __name__ == "__main__":
    main()
