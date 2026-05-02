#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AU_run_all.py"""
import os, sys, subprocess, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

SCRIPTS = [
    # 行情+持仓（日度）
    "AU_FUT_CLOSE.py",
    "AU_FUT_OI.py",
    # 宏观因子（日度）
    "AU_美国10年期国债收益率（名义）.py",   # 美国10年期国债收益率（TIPS代理）
    "AU_美联储联邦基金目标利率.py",        # 美联储联邦基金利率
    "AU_VIX.py",             # VIX恐慌指数（FRED VIXCLS）
    "AU_金银比_AUAG.py",        # 金银比（SGE黄金/白银现货）
    "AU_COMEX_AU.py",        # COMEX黄金期货价格（USD/盎司）
    # 美国宏观（月度）
    "AU_US_NFP.py",          # 美国新增非农就业人数
    "AU_US_CPI.py",          # 美国CPI同比增速
    # 期现/现货
    "AU_SGE现货基准价.py",
    "AU_期现基差.py",
    # 持仓/库存（周/月度）
    "AU_CFTC非商业净多.py",  # CFTC黄金非商业净持仓（周度）
    "AU_央行黄金储备.py",    # 中国央行黄金储备（月度）
    # L4兜底因子（无免费源）
    "AU_DXY美元指数.py",             # DXY美元指数（Yahoo 403, L4回补）
    "AU_SPDR黄金ETF持仓量.py",         # SPDR黄金ETF持仓（SPDR网站404, L4回补）
    "AU_SHFE沪金前20会员净持仓.py",       # SHFE沪金前20净持仓（AKShare DCE不支持SHFE, L4回补）
    "AU_美联储点阵图（2026年末利率预测中位数）.py",         # Fed点阵图（FOMC网站404, L4回补）
]

def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print("[SKIP] {} not found".format(name)); return None
    print(">> Running {}...".format(name))
    try:
        # Suppress all output (tqdm + print chars can cause GBK encode errors in parent)
        r = subprocess.run([sys.executable, path, "--auto"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if r.returncode == 0:
            print("[OK] {} done".format(name)); return True
        else:
            print("[WARN] {} exit code:{}".format(name, r.returncode)); return False
    except Exception as e:
        print("[ERR] {} exception: {}".format(name, e)); return False

def main():
    print("=" * 50)
    print("AU data collection started @ {}".format(datetime.now()))
    print("Scripts to run: {}".format(len(SCRIPTS)))
    print("=" * 50)
    t0 = time.time(); ok, fail = 0, 0
    for s in SCRIPTS:
        r = run_script(s)
        if r: ok += 1
        else: fail += 1
        time.sleep(0.5)
    print("=" * 50)
    print("AU data collection done  time:{:.1f}s  ok:{}/{}".format(time.time()-t0, ok, ok+fail))
    print("=" * 50)

if __name__ == "__main__":
    main()
