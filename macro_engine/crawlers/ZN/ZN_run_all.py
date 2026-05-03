#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys, os, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = ['ZN_沪锌期货收盘价.py', 'ZN_沪锌期货持仓量.py', "ZN_沪锌期货库存.py"]

def main():
    sep = "=" * 50
    print(sep)
    print("ZN @ " + datetime.now().isoformat())
    print(sep)
    t0 = time.time()
    ok = 0
    for s in SCRIPTS:
        path = os.path.join(SCRIPT_DIR, s)
        if not os.path.exists(path):
            print("? " + s)
            continue
        print(">> " + s)
        try:
            r = subprocess.run([sys.executable, path, "--auto"], capture_output=True, timeout=30)
            try:
                out = r.stdout.decode("utf-8", errors="replace")
            except (ValueError, IndexError):
                out = str(r.stdout)
            for line in out.strip().split("\r\n")[-3:]:
                if line.strip():
                    try:
                        print("   " + line[:120])
                    except (ValueError, IndexError):
                        pass
            if r.returncode == 0:
                ok += 1
        except Exception as e:
            print("   Exception: " + str(e)[:80])
    print(sep)
    elapsed = time.time() - t0
    print("ZN Done " + "%.1fs OK=%d/%d" % (elapsed, ok, len(SCRIPTS)))
    print(sep)

if __name__ == "__main__":
    main()
