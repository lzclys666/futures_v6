#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_run_all.py - 焦煤爬虫总控
自动脚本走 --auto，手动兜底脚本走 --manual
"""
import subprocess, sys, os, datetime

# Windows UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# === 自动化脚本(免费数据源) ===
daily_free = [
    "JM_抓取焦煤期货持仓量.py",      # JM_POS_OI
    "JM_计算焦煤月差.py",            # JM_SPD_CONTRACT
    "JM_计算焦煤期现基差.py",         # JM_SPD_BASIS(现货价付费，当前L4兜底)
    "JM_计算焦煤动力煤比价.py",       # JM_SPD_ZC
]

monthly = [
    "JM_抓取焦煤进口量.py",           # JM_IMPORT
]

auto_scripts = daily_free + monthly

# === 手动兜底脚本(付费数据源，DB回补+手动输入) ===
manual_scripts = [
    "JM_矿山开工率.py",               # JM_SUPPLY_MINE_RATE - Mysteel(年费)
    "JM_精煤产量.py",                 # JM_SUPPLY_WASHED_OUTPUT - 统计局月频
    "JM_甘其毛都通关车数.py",          # JM_SUPPLY_GQMD_CARS - 汾渭(年费)
    "JM_三大口岸库存.py",             # JM_INV_THREE_PORTS - Mysteel(年费)
    "JM_铁水产量.py",                 # JM_DEMAND_HOT_METAL - Mysteel(年费)
    "JM_焦企产能利用率.py",            # JM_DEMAND_COKING_RATE - Mysteel(年费)
    "JM_焦化利润.py",                 # JM_COST_COKING_PROFIT - Mysteel(年费)
    "JM_焦化厂炼焦煤库存.py",          # JM_INV_COKING_PLANT - Mysteel(年费)
    "JM_钢厂炼焦煤库存.py",            # JM_INV_STEEL_PLANT - Mysteel(年费)
    "JM_澳煤进口盈亏.py",             # JM_COST_AU_PROFIT - 普氏(付费)
    "JM_甘其毛都口岸库存.py",          # JM_INV_GQMD - 汾渭(年费)
    "JM_蒙煤口岸成本.py",             # JM_COST_MONGOLIA - 汾渭(年费)
    "JM_蒙煤山西煤价差.py",            # JM_SPD_MG_SX - 汾渭(年费)
]

def run_scripts(scripts, mode="auto"):
    success, fail, skip = 0, 0, 0
    for script in scripts:
        script_path = CURRENT_DIR / script
        if not script_path.exists():
            print(f"  [跳过] {script} 不存在"); skip += 1; continue

        print(f"\n>>> {script}... ({mode})")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        args = [sys.executable, str(script_path)]
        if mode == "auto":
            args.append("--auto")
        elif mode == "manual":
            args.append("--manual")

        try:
            result = subprocess.run(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding='utf-8', errors='replace',
                timeout=120, cwd=str(CURRENT_DIR), env=env
            )
            out = result.stdout or ""
            if out.strip():
                print(out.strip())
            if result.stderr:
                print(f"[stderr] {result.stderr.strip()}")

            if result.returncode == 0:
                if "跳过" in out or "非交易日" in out:
                    skip += 1
                else:
                    success += 1
            else:
                fail += 1
        except Exception as e:
            fail += 1
            print(f"  [异常] {e}")
    return success, fail, skip

def run_all(mode="auto"):
    now = datetime.datetime.now()
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}.log"

    print("=" * 60)
    print(f"JM 数据采集 @ {now}")
    print(f"自动化: {len(auto_scripts)}, 手动兜底: {len(manual_scripts)}")
    print("=" * 60)

    auto_ok, auto_fail, auto_skip = run_scripts(auto_scripts, mode=mode)

    if mode == "manual":
        man_ok, man_fail, man_skip = run_scripts(manual_scripts, mode="manual")
    else:
        man_ok, man_fail, man_skip = run_scripts(manual_scripts, mode="auto")

    total_ok = auto_ok + man_ok
    total_fail = auto_fail + man_fail
    total_skip = auto_skip + man_skip

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*60}\nJM采集 @ {now} | 自动={auto_ok}/{len(auto_scripts)} 手动={man_ok}/{len(manual_scripts)}\n{'='*60}\n")

    print(f"\n{'='*60}")
    print(f"结果: 成功={total_ok} 失败={total_fail} 跳过={total_skip}")
    print(f"  自动化: {auto_ok}/{len(auto_scripts)}")
    print(f"  手动兜底: {man_ok}/{len(manual_scripts)} (DB回补)")
    print(f"{'='*60}")

if __name__ == "__main__":
    mode = "auto"
    if "--manual" in sys.argv:
        mode = "manual"
    run_all(mode)
