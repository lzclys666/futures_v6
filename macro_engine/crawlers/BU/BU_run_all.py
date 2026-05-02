#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU（沥青）爬虫总控脚本
基于AKShare的真实数据采集版本
"""
import os
import sys
import datetime
import subprocess
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
LOG_DIR = CURRENT_DIR.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

scripts = [
    "BU_沥青期货收盘价.py",
    "BU_沥青期货仓单.py",
    "BU_沥青期货净持仓.py",
    "BU_沥青期现基差.py",
    "BU_华东沥青市场价格.py",
    "BU_沥青与布伦特原油价差.py",
    "BU_美元兑人民币汇率.py",
    "BU_沥青社会库存.py",
]

def run_all():
    _sym = "BU"
    _name = "沥青"
    now = datetime.datetime.now()
    log_file = LOG_DIR / (now.strftime('%Y-%m-%d') + '_' + _sym + '.log')

    print("=" * 50)
    print('[REAL] BU (沥青) AKShare数据采集版')
    print("待执行脚本数: " + str(len(scripts)))
    print("=" * 50)

    success_count = 0
    failures = []

    with open(log_file, "a", encoding="utf-8") as log:
        sep50 = '=' * 50
        log_write = sep50 + '\n' + _sym + ' start @ ' + str(now) + '\n' + sep50 + '\n'
        log.write(log_write)

        for script in scripts:
            script_path = CURRENT_DIR / script
            if not script_path.exists():
                msg = '[SKIP] script not found: ' + script
                print("[WARN] " + msg)
                log.write(msg + '\n')
                failures.append((script, 'file_not_found'))
                continue

            print(">>> " + script + "...")
            log.write('--- ' + script + ' @ ' + str(datetime.datetime.now()) + ' ---\n')

            cmd = [sys.executable, str(script_path), "--auto"]

            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                    cwd=str(CURRENT_DIR),
                    env=env,
                )

                log.write(result.stdout if result.stdout else "")
                if result.stderr:
                    log.write('[stderr] ' + result.stderr + '\n')

                if result.returncode == 0:
                    success_count += 1
                    print("[OK] " + script)
                else:
                    print("[WARN] " + script + " err=" + str(result.returncode))
                    failures.append((script, 'err=' + str(result.returncode)))

            except subprocess.TimeoutExpired:
                msg = script + ' timeout'
                print("[WARN] " + msg)
                failures.append((script, 'timeout'))

            except Exception as e:
                msg = script + ' exception: ' + str(e)
                print("[WARN] " + msg)
                failures.append((script, str(e)))

        end_time = datetime.datetime.now()
        duration = (end_time - now).total_seconds()

        sep = '=' * 50
        summary = "\n" + sep + "\n"
        summary += _sym + " done @ " + str(end_time) + "\n"
        summary += "duration: " + str(round(duration, 1)) + "s\n"
        summary += "success: " + str(success_count) + "/" + str(len(scripts)) + "\n"
        if failures:
            summary += "failed " + str(len(failures)) + "\n"
            for n, r in failures:
                summary += "  - " + n + ": " + r + "\n"
        else:
            summary += 'all ok\n'
        summary += sep + "\n"

        log.write(summary)
        print(summary)


if __name__ == "__main__":
    run_all()
