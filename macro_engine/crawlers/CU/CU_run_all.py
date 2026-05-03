# -*- coding: utf-8 -*-
"""
CU_run_all.py - 沪铜日度数据采集总调度
批次1: 免费数据源 (AKShare) - 7个因子
批次2: 付费/无免费数据源 - 14个因子 (手动输入)
"""
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 批次1: 免费数据源
BATCH1 = [
    ("CU_抓取库存.py",       "CU_INV_SHFE"),
    ("CU_抓取SHFE仓单.py",    "CU_WRT_SHFE"),
    ("CU_计算基差.py",        "CU_SPD_BASIS"),
    ("CU_抓取期货持仓量.py",   "CU_FUT_OI"),
    ("CU_抓取持仓排名.py",     "CU_POS_NET"),
    ("CU_抓取LME库存.py",     "CU_INV_LME"),
    ("CU_计算近远月价差.py",   "CU_SPD_CONTRACT"),
    ("../CU_NI/CU_NI_LME升贴水.py", "CU_LME_SPREAD/CU_LME_SPREAD_DIFF/CU_LME_SPREAD_EVENT"),
]

# 批次2: 付费/无免费数据源
BATCH2 = [
    ("CU_批次2_手动输入.py",   "BATCH2"),
]

ALL = BATCH1 + BATCH2

def run_script(name, factor_hint=""):
    script_path = os.path.join(SCRIPT_DIR, name)
    print(f"\n{'='*60}")
    print(f">>> {name} {f'(target: {factor_hint})' if factor_hint else ''}")
    result = subprocess.run(
        [sys.executable, script_path, "--auto"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def main():
    print("CU沪铜数据采集开始")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本目录: {SCRIPT_DIR}")

    results = []
    for name, hint in ALL:
        ok = run_script(name, hint)
        results.append((name, ok))

    print(f"\n{'='*60}")
    print("CU采集结果汇总:")
    success = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print(f"批次1: {sum(1 for n,_ in BATCH1 if any(n in r[0] for r in results[:len(BATCH1)]))}/{len(BATCH1)}")
    print(f"批次2: {sum(1 for n,_ in BATCH2 if any(n in r[0] for r in results[len(BATCH1):]))}/{len(BATCH2)}")

if __name__ == "__main__":
    main()
