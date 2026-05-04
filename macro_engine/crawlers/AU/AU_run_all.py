#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_run_all.py - 沪金期货数据采集调度脚本

调度顺序:
  行情持仓 → 美国宏观 → 期现/现货 → 持仓/库存 → L4兜底
"""
import subprocess, sys, os, time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))
from common.db_utils import ensure_table, get_pit_dates

# 自动模式脚本（免费源）
AUTO_SCRIPTS = [
    # 行情+持仓（日度）
    'AU_期货收盘价.py',
    'AU_期货持仓量.py',
    # 宏观因子（日度）
    'AU_美国10年期国债收益率（名义）.py',
    'AU_美联储联邦基金目标利率.py',
    'AU_恐慌指数.py',
    'AU_金银比_AUAG.py',
    'AU_COMEX白银.py',
    # 美国宏观（月度）
    'AU_美国非农.py',
    'AU_美国CPI.py',
    # 期现/现货
    'AU_SGE现货基准价.py',
    'AU_期现基差.py',
    # 持仓/库存（周/月度）
    'AU_CFTC非商业净多.py',
    'AU_央行黄金储备.py',
    # L4兜底因子（无免费源）
    'AU_DXY美元指数.py',
    'AU_SPDR黄金ETF持仓量.py',
    'AU_SHFE沪金前20会员净持仓.py',
    'AU_美联储点阵图（2026年末利率预测中位数）.py',
]

# 手动模式脚本（付费/手动录入）
MANUAL_SCRIPTS = []


def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        return False, f"{name} not found"
    try:
        r = subprocess.run(
            [sys.executable, '-X', 'utf8=1', path, '--auto'],
            capture_output=True, timeout=60
        )
        try:
            out = r.stdout.decode("utf-8", errors="replace")
        except Exception:
            out = str(r.stdout)
        ok = r.returncode == 0
        return ok, out[-300:] if out else ""
    except Exception as e:
        return False, str(e)[:80]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="免费源自动采集")
    parser.add_argument("--manual", action="store_true", help="手动录入脚本")
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sep = "=" * 60
    print(sep)
    print(f"AU Data Collection @ {now}")
    print(f"日期: pub={pub_date} obs={obs_date}")
    print(sep)

    scripts = []
    mode = "unknown"
    if args.auto:
        scripts = AUTO_SCRIPTS
        mode = f"auto - {len(scripts)} 个免费源脚本"
    elif args.manual:
        scripts = MANUAL_SCRIPTS
        mode = f"manual - {len(scripts)} 个付费/手动录入脚本"
    else:
        # 默认auto
        scripts = AUTO_SCRIPTS
        mode = f"auto - {len(scripts)} 个免费源脚本（默认）"

    print(f"[MODE] {mode}")
    print("-" * 60)

    t0 = time.time()
    ok = 0
    for s in scripts:
        print(f">>> {s}...")
        success, detail = run_script(s)
        if detail:
            for line in detail.split('\n'):
                if line.strip():
                    print(f"    {line[:100]}")
        if success:
            print(f"[OK] {s} done")
            ok += 1
        else:
            print(f"[ERR] {s} failed")
        time.sleep(0.5)
    print(sep)
    elapsed = time.time() - t0
    print(f"完成: {ok}/{len(scripts)} 成功, 耗时 {elapsed:.1f}s")
    print(sep)


if __name__ == "__main__":
    main()
