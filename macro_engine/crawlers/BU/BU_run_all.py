#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU（沥青）爬虫总控脚本

调度顺序:
  活跃脚本: 收盘价 → 净持仓 → 基差 → 现货价 → 布伦特价差 → 汇率 → 库存
  stub脚本: 仓单 → 开工率 → 高速公路 → 消费者信心
"""
import subprocess, sys, os, time, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPT_DIR / ".."))
from common.db_utils import ensure_table, get_pit_dates

# 活跃脚本（免费源）
AUTO_SCRIPTS = [
    "BU_沥青期货收盘价.py",
    "BU_沥青期货净持仓.py",
    "BU_沥青期现基差.py",
    "BU_华东沥青市场价格.py",
    "BU_沥青与布伦特原油价差.py",
    "BU_美元兑人民币汇率.py",
    "BU_沥青社会库存.py",
]

# stub脚本（无免费源，仅L4回补）
STUB_SCRIPTS = [
    "BU_沥青期货仓单.py",
    "BU_炼厂沥青开工率.py",
    "BU_全国高速公路整车流量.py",
    "BU_消费者信心指数.py",
]


def run_script(name):
    path = SCRIPT_DIR / name
    if not path.exists():
        return False, f"{name} not found"
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        r = subprocess.run(
            [sys.executable, '-X', 'utf8=1', str(path), '--auto'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", errors="replace",
            timeout=120, env=env
        )
        out = (r.stdout or "").strip()
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
    now = datetime.datetime.now()
    log_file = LOG_DIR / (now.strftime('%Y-%m-%d') + '_BU.log')

    sep = "=" * 60
    print(sep)
    print(f"BU Data Collection @ {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"日期: pub={pub_date} obs={obs_date}")
    print(sep)

    scripts = AUTO_SCRIPTS + STUB_SCRIPTS
    mode = "auto" if not args.manual else "manual"
    print(f"[MODE] {mode} - {len(scripts)} 个脚本（{len(AUTO_SCRIPTS)} 活跃 + {len(STUB_SCRIPTS)} stub）")
    print("-" * 60)

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{sep}\nBU start @ {now}\npub={pub_date} obs={obs_date}\n{sep}\n")

        t0 = time.time()
        ok_count = 0
        failures = []

        for s in scripts:
            print(f">>> {s}...")
            log.write(f'--- {s} @ {datetime.datetime.now()} ---\n')
            success, detail = run_script(s)
            if detail:
                for line in detail.split('\n'):
                    if line.strip():
                        print(f"    {line[:100]}")
                log.write(detail + '\n')
            if success:
                print(f"[OK] {s} done")
                ok_count += 1
            else:
                print(f"[ERR] {s} failed")
                failures.append(s)
            time.sleep(1)

        elapsed = time.time() - t0
        summary = f"\n{sep}\n完成: {ok_count}/{len(scripts)} 成功, 耗时 {elapsed:.1f}s\n"
        if failures:
            summary += f"失败: {', '.join(failures)}\n"
        summary += sep

        log.write(summary + '\n')
        print(summary)


if __name__ == "__main__":
    main()
