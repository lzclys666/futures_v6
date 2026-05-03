#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HC_run_all.py - 热轧卷板数据采集（subprocess模式）"""
import os, sys, subprocess, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

scripts = [
    "HC_制造业PMI.py",
    "HC_我的钢铁网热卷现货价格.py",
    "HC_汽车产量.py",
    "HC_热卷-螺纹钢跨品种价差.py",
    "HC_热卷仓单库存.py",
    "HC_热卷期现基差.py",
    "HC_热卷期货净持仓.py",
    "HC_热卷期货合约间价差.py",
    "HC_热卷期货近远月价差.py",
    "HC_热卷社会库存总量.py",
    "HC_热轧卷板期货持仓量.py",
    "HC_热轧卷板期货收盘价.py",
    "HC_钢厂热卷库存周度.py",
]

def run_all():
    now = datetime.datetime.now()
    log_file = LOG_DIR / f"{now.strftime('%Y-%m-%d')}_HC.log"

    print("=" * 50)
    print(f"HC Data Collection @ {now}")
    print(f"Scripts: {len(scripts)}")
    print("=" * 50)

    success_count = 0
    failures = []

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*50}\nHC Start @ {now}\n{'='*50}\n")

        for script in scripts:
            script_path = CURRENT_DIR / script
            if not script_path.exists():
                msg = f"[SKIP] {script} not found"
                print(msg); log.write(f"{msg}\n")
                failures.append((script, "not found"))
                continue

            print(f">>> {script}...")
            log.write(f"\n--- {script} @ {datetime.datetime.now()} ---\n")

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            try:
                result = subprocess.run(
                    [sys.executable, "-X", "utf8=1", str(script_path), "--auto"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120,
                    cwd=str(CURRENT_DIR),
                    env=env
                )

                log.write(result.stdout if result.stdout else "")
                if result.stderr:
                    log.write(f"[stderr] {result.stderr}\n")

                if result.returncode == 0:
                    success_count += 1
                    print(f"[OK] {script} done")
                else:
                    print(f"[WARN] {script} exit:{result.returncode}")
                    failures.append((script, f"exit {result.returncode}"))

            except subprocess.TimeoutExpired:
                msg = f"{script} TIMEOUT"
                print(f"[WARN] {msg}")
                failures.append((script, "timeout"))
            except Exception as e:
                msg = f"{script} exception: {e}"
                print(f"[ERR] {msg}")
                failures.append((script, str(e)))

        duration = (datetime.datetime.now() - now).total_seconds()
        print(f"\n{'='*50}")
        print(f"HC Done  {duration:.1f}s  {success_count}/{len(scripts)}")
        if failures:
            for n, r in failures:
                print(f"  - {n}: {r}")
        else:
            print("[OK] All done")
        print(f"{'='*50}")
        log.write(f"\n[Done] {success_count}/{len(scripts)}\n")

if __name__ == "__main__":
    run_all()
