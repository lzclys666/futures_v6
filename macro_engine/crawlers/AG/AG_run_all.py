#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_run_all.py - 白银数据采集总调度

支持 --auto/--manual 双模式:
- --auto: 只跑活跃脚本（免费源）
- --manual: 只跑需付费/手动录入的脚本
- 默认: --auto
"""
import os, sys, subprocess, time, argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# 确保 common 模块可导入
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..'))

from common.db_utils import ensure_table, get_pit_dates

# === 活跃脚本（免费源）===
auto_scripts = [
    ("AG_抓取黄金白银比.py", "金银比"),
    ("AG_抓取期货日行情.py", "期货日行情"),
    ("AG_抓取净持仓.py", "净持仓"),
    ("AG_抓取COMEX白银库存.py", "COMEX白银库存"),
    ("AG_抓取COMEX黄金库存.py", "COMEX黄金库存"),
    ("AG_抓取白银ETF持仓.py", "白银ETF持仓"),
    ("AG_抓取汇率.py", "USDCNY汇率"),         # ⚠️ 必须在比价之前
    ("AG_抓取CPI.py", "美国CPI"),
    ("AG_抓取TIPS.py", "TIPS实际收益率"),
    ("AG_计算沪银COMEX比价.py", "沪银COMEX比价"),  # 依赖汇率
]

# === 手动录入/付费源脚本 ===
manual_scripts = [
    ("AG_抓取CFTC白银持仓.py", "CFTC白银持仓"),      # ⛔ 无免费源
    ("AG_抓取SHFE白银仓单.py", "SHFE白银仓单"),      # ⛔ 无免费源
    ("AG_抓取现货价.py", "沪银现货价"),               # ⛔ 无免费源
    ("AG_抓取美元指数.py", "美元指数"),               # ⛔ 无免费源
    ("AG_计算期现基差.py", "期现基差"),               # ⛔ 依赖现货价
]


def run_script(name, desc):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        print(f"[WARN] {name} not found"); return None
    print(f">>> {desc} ({name})...")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, "-X utf8=1", path, "--auto"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=60, env=env
        )
        out = (r.stdout or "").strip()
        if out:
            for line in out.splitlines()[-3:]:
                print(f"    {line}")
        if r.returncode == 0:
            print(f"[OK] {desc} done"); return True
        else:
            print(f"[WARN] {desc} exit:{r.returncode}"); return False
    except Exception as e:
        print(f"[ERR] {desc} exception: {e}"); return False


def main():
    parser = argparse.ArgumentParser(description="AG数据采集")
    parser.add_argument('--auto', action='store_true', help='只跑免费源脚本（默认）')
    parser.add_argument('--manual', action='store_true', help='只跑付费源/手动录入脚本')
    args = parser.parse_args()

    # 初始化数据库表
    ensure_table()

    pub_date, obs_date = get_pit_dates()
    print("=" * 60)
    print(f"AG Data Collection @ {datetime.now()}")
    print(f"日期: pub={pub_date} obs={obs_date}")
    print("=" * 60)

    if args.manual:
        scripts = manual_scripts
        print(f"[MODE] manual - {len(scripts)} 个付费/手动录入脚本")
    else:
        scripts = auto_scripts
        print(f"[MODE] auto - {len(scripts)} 个免费源脚本")

    print("-" * 60)
    t0 = time.time()
    ok, fail = 0, 0
    for name, desc in scripts:
        r = run_script(name, desc)
        if r:
            ok += 1
        else:
            fail += 1
        time.sleep(1)

    print("=" * 60)
    print(f"完成: {ok}/{ok+fail} 成功, 耗时 {time.time()-t0:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
