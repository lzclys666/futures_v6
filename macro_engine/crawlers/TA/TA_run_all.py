#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TA_run_all.py - PTA数据采集总调度
"""
import os, sys, subprocess, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    "TA_抓取PTA库存.py",
    "TA_抓取郑商所仓单.py",
    "TA_抓取期货持仓.py",
    "TA_抓取汇率.py",
    "TA_抓取BRENT价格.py",
    "TA_PTA成交量.py",
    "TA_抓取PX价格.py",
    "TA_抓取PTA成本.py",
    "TA_抓取聚酯开工率.py",
    "TA_抓取PTA开工率.py",
    "TA_批次2_手动输入.py",
    "TA_计算基差.py",
]


def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print(f"[SKIP] {name} not found")
        return None
    try:
        r = subprocess.run(
            [sys.executable, path, "--auto"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60
        )
        # 检查是否写入成功（脚本可能在stderr有warning但实际成功）
        # 成功标志: 包含"写入成功"或"DB写入"或"OK"
        out = (r.stdout or "") + (r.stderr or "")
        ok_markers = ["写入成功", "DB", "[OK]", "OK:", "完成", "[跳过]", "[永久跳过]", "mode=auto", "[L4]", "[INFO]"]
        is_ok = any(m in out for m in ok_markers) and "Traceback" not in out
        return True if is_ok else False
    except Exception:
        return False


def main():
    print("=" * 50)
    print(f"TA PTA 数据采集 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    t0 = time.time()
    ok, fail = 0, 0
    for s in SCRIPTS:
        r = run_script(s)
        status = "[OK]" if r else "[FAIL]"
        print(f"  {status} {s}")
        if r:
            ok += 1
        elif r is False:
            fail += 1
        time.sleep(1)
    print("=" * 50)
    print(f"完成: {ok}/{ok+fail}  耗时:{time.time()-t0:.1f}s")
    print("=" * 50)


if __name__ == "__main__":
    main()
