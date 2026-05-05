#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_run_all.py - 焦煤爬虫总控
自动脚本走 --auto，手动兜底脚本走 --manual

调度分类:
- daily_free: 每日自动采集（免费数据源）
- monthly: 月度自动采集（免费数据源）
- manual_scripts: 手动兜底（付费数据源，--manual模式才运行）
"""
import subprocess, sys, os, datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'common'))
from db_utils import get_pit_dates, ensure_table

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
            print(f"  [跳过] {script} 不存在")
            skip += 1
            continue

        print(f"\n>>> {script}... ({mode})")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        args = [sys.executable, '-X', 'utf8=1', str(script_path)]
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
        import time
        time.sleep(1)
    return success, fail, skip


def run_all(mode="auto"):
    pub_date, obs_date = get_pit_dates()
    ensure_table()

    now = datetime.datetime.now()
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}.log"

    print("=" * 60)
    print(f"JM 数据采集 @ {now}")
    print(f"pub_date={pub_date} obs_date={obs_date}")
    print(f"自动化: {len(auto_scripts)}, 手动兜底: {len(manual_scripts)}")
    print(f"模式: {mode}")
    print("=" * 60)

    auto_ok, auto_fail, auto_skip = run_scripts(auto_scripts, mode=mode)

    # auto模式不运行manual脚本（它们会检测--auto后立即退出，但仍浪费资源）
    if mode == "manual":
        man_ok, man_fail, man_skip = run_scripts(manual_scripts, mode="manual")
    else:
        print(f"\n[AUTO模式] 跳过 {len(manual_scripts)} 个手动兜底脚本（付费数据源）")
        man_ok, man_fail, man_skip = 0, 0, len(manual_scripts)

    total_ok = auto_ok + man_ok
    total_fail = auto_fail + man_fail
    total_skip = auto_skip + man_skip

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*60}\n")
        log.write(f"JM采集 @ {now} | pub={pub_date} obs={obs_date} | mode={mode}\n")
        log.write(f"自动={auto_ok}/{len(auto_scripts)} 手动={man_ok}/{len(manual_scripts)}\n")
        log.write(f"{'='*60}\n")

    print(f"\n{'='*60}")
    print(f"JM Done  {now.strftime('%H:%M:%S')}  {total_ok+total_fail+total_skip}/{len(auto_scripts)+len(manual_scripts)}")
    print(f"  自动: {auto_ok}/{len(auto_scripts)}")
    print(f"  手动: {man_ok}/{len(manual_scripts)} (DB回补)")
    print(f"{'='*60}")


if __name__ == "__main__":
    mode = "auto"
    if "--manual" in sys.argv:
        mode = "manual"
    run_all(mode)
