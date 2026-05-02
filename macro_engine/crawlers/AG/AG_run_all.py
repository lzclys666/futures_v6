#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG_run_all.py - 白银数据采集总调度"""
import os, sys, subprocess, time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# 活跃脚本（已移除永久跳过/废弃脚本）
SCRIPTS = [
    "AG_抓取黄金白银比.py",       # 金银比（L1 SGE现货）
    "AG_抓取期货日行情.py",       # AG_FUT_CLOSE + AG_POS_NET
    "AG_抓取净持仓.py",           # AG_POS_NET（冗余但无害）
    "AG_抓取COMEX白银库存.py",    # AG_INV_COMEX_SILVER（已修复Bug）
    "AG_抓取COMEX黄金库存.py",    # AG_INV_COMEX_GOLD
    "AG_抓取白银ETF持仓.py",      # AG_DEM_ETF_HOLDING（已修复Bug）
    "AG_抓取汇率.py",             # AG_COST_USDCNY
    "AG_抓取CPI.py",              # AG_MACRO_US_CPI_YOY
    "AG_抓取TIPS.py",             # AG_MACRO_US_TIPS_10Y
    "AG_计算沪银COMEX比价.py",    # AG_SPD_SHFE_COMEX
    # 以下已永久跳过/废弃，不再运行：
    # AG_抓取现货价.py         ⛔ AKShare无AG现货价数据
    # AG_抓取SHFE白银仓单.py   ⛔ SHFE仓单API失效
    # AG_抓取CFTC白银持仓.py   ⛔ AKShare无CFTC白银数据
    # AG_抓取美元指数.py        ⛔ DXY无免费数据源
    # AG_抓取黄金白银比_FRED.py ⛔ 已废弃（由AG_抓取黄金白银比.py替代）
]

def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print(f"[WARN] {name} not found"); return None
    print(f">>> Running {name}...")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, path, "--auto"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, env=env)
        out = (r.stdout or "").strip()
        if out:
            for line in out.splitlines()[-4:]: print(f"    {line}")
        if r.returncode == 0:
            print(f"[OK] {name} done"); return True
        else:
            print(f"[WARN] {name} exit:{r.returncode}"); return False
    except Exception as e:
        print(f"[ERR] {name} exception: {e}"); return False

def main():
    print("=" * 50)
    print(f"AG Data Collection @ {datetime.now()}")
    print(f"Scripts: {len(SCRIPTS)}")
    print("=" * 50)
    t0 = time.time(); ok, fail = 0, 0
    for s in SCRIPTS:
        r = run_script(s)
        if r: ok += 1
        else: fail += 1
        time.sleep(1)
    print("=" * 50)
    print(f"AG Done  {time.time()-t0:.1f}s  {ok}/{ok+fail}")
    print("=" * 50)

if __name__ == "__main__":
    main()
