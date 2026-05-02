# -*- coding: utf-8 -*-
"""
I_run_all.py - 铁矿石日度数据采集总调度
批次1: 免费数据源 (AKShare) - 5个因子
批次2: 付费/无免费数据源 - 11个因子 (手动输入)
注意: DCE铁矿石持仓排名接口不稳定，I_POS_NET暂归批次2
"""
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 批次1: 免费数据源
BATCH1 = [
    ("I_抓取港口库存.py",    "I_STK_PORT"),
    ("I_计算基差.py",        "I_SPD_BASIS"),
    ("I_抓取期货持仓量.py",   "I_FUT_OI"),
    ("I_抓取期货收盘价.py",   "I_FUT_MAIN"),
    ("I_计算近远月价差.py",   "I_SPD_CONTRACT"),
]

# 批次2: 付费/无免费数据源
BATCH2 = [
    ("I_批次2_手动输入.py",   "BATCH2"),
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
    print("铁矿石数据采集开始")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本目录: {SCRIPT_DIR}")

    results = []
    for name, hint in ALL:
        ok = run_script(name, hint)
        results.append((name, ok))

    print(f"\n{'='*60}")
    print("铁矿石采集结果汇总:")
    success = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")
    print(f"批次1: {sum(1 for n,_ in BATCH1)}/{len(BATCH1)}")
    print(f"批次2: {sum(1 for n,_ in BATCH2)}/{len(BATCH2)}")

if __name__ == "__main__":
    main()
