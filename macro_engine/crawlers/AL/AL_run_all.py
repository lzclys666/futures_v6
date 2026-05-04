#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_run_all.py - 沪铝爬虫总控

支持 --auto/--manual 双模式:
- --auto: 只跑活跃脚本（免费源）
- --manual: 只跑需付费/手动录入的脚本
- 默认: --auto
"""
import os, sys, subprocess, datetime, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(CURRENT_DIR.parent))
from common.db_utils import ensure_table, get_pit_dates

# === 活跃脚本（免费源）===
auto_scripts = [
    ("AL_抓取LME铝库存.py", "LME铝库存"),
    ("AL_抓取LME铝价_铝道网.py", "LME铝价"),
    ("AL_抓取净持仓.py", "净持仓"),
    ("AL_计算持仓集中度.py", "持仓集中度"),
    ("AL_计算近远月价差.py", "近远月价差"),
    ("AL_计算SHFE_LME比价.py", "SHFE_LME比价"),  # 依赖LME铝价
    ("AL_计算铝铜比价.py", "铝铜比价"),
]

# === 手动录入/付费源脚本 ===
manual_scripts = [
    ("AL_抓取上期所沪铝仓单.py", "SHFE铝仓单"),      # ⛔ 无免费源
    ("AL_计算期现基差.py", "期现基差"),               # ⛔ 无免费源
]


def run_script(name, desc):
    script_path = CURRENT_DIR / name
    if not script_path.exists():
        print(f"[WARN] {name} not found"); return None
    print(f">>> {desc} ({name})...")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        r = subprocess.run(
            [sys.executable, "-X", "utf8=1", str(script_path)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=120, cwd=str(CURRENT_DIR), env=env
        )
        out = (r.stdout or "").strip()
        if out:
            for line in out.splitlines()[-3:]:
                print(f"    {line}")
        if r.returncode == 0:
            print(f"[OK] {desc} done"); return True
        else:
            print(f"[WARN] {desc} exit:{r.returncode}"); return False
    except subprocess.TimeoutExpired:
        print(f"[WARN] {name} TIMEOUT (>120s)"); return False
    except Exception as e:
        print(f"[ERR] {name} exception: {e}"); return False


def main():
    parser = argparse.ArgumentParser(description="AL数据采集")
    parser.add_argument('--auto', action='store_true', help='只跑免费源脚本（默认）')
    parser.add_argument('--manual', action='store_true', help='只跑付费源/手动录入脚本')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()

    print("=" * 60)
    print(f"AL Data Collection @ {datetime.datetime.now()}")
    print(f"日期: pub={pub_date} obs={obs_date}")
    print("=" * 60)

    if args.manual:
        scripts = manual_scripts
        print(f"[MODE] manual - {len(scripts)} 个付费/手动录入脚本")
    else:
        scripts = auto_scripts
        print(f"[MODE] auto - {len(scripts)} 个免费源脚本")

    print("-" * 60)
    t0 = datetime.datetime.now()
    ok, fail = 0, 0

    for name, desc in scripts:
        r = run_script(name, desc)
        if r:
            ok += 1
        else:
            fail += 1
        import time; time.sleep(1)

    duration = (datetime.datetime.now() - t0).total_seconds()
    print("=" * 60)
    print(f"完成: {ok}/{ok+fail} 成功, 耗时 {duration:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
