#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RB_run_all.py - 螺纹钢爬虫总控
"""
import subprocess, sys, os, datetime

# Windows UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 批次1: 完全自动化因子
auto_scripts = [
    "RB_抓取螺纹钢库存.py",          # RB_INV_STEEL
    "RB_抓取上期所螺纹钢仓单.py",     # RB_INV_SHFE
    "RB_抓取净持仓.py",              # RB_POS_NET
    "RB_计算持仓集中度.py",          # RB_POS_CONCENTRATION
    "RB_计算期现基差.py",            # RB_SPD_BASIS
    "RB_计算近远月价差.py",          # RB_SPD_CONTRACT
    "RB_计算螺纹钢热卷比价.py",       # RB_SPD_RB_HC
]

# 批次2: 手动输入兜底（付费数据源）
manual_scripts = [
    "RB_批次2_手动输入.py",
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
                success += 1
            else:
                fail += 1
        except Exception as e:
            fail += 1
            print(f"  [异常] {e}")
    return success, fail, skip

def run_all():
    now = datetime.datetime.now()
    print("=" * 60)
    print(f"RB 数据采集 @ {now}")
    print(f"自动化: {len(auto_scripts)}, 手动兜底: {len(manual_scripts)}")
    print("=" * 60)

    auto_ok, auto_fail, auto_skip = run_scripts(auto_scripts)
    man_ok, man_fail, man_skip = run_scripts(manual_scripts)

    total_ok = auto_ok + man_ok
    total_fail = auto_fail + man_fail
    total_skip = auto_skip + man_skip

    print(f"\n{'='*60}")
    print(f"结果: 成功={total_ok} 失败={total_fail} 跳过={total_skip}")
    print(f"  自动化: {auto_ok}/{len(auto_scripts)}")
    print(f"  手动兜底: {man_ok}/{len(manual_scripts)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    run_all()
