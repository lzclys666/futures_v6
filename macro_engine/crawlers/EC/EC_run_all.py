# -*- coding: utf-8 -*-
"""
EC_run_all.py - 集运指数数据采集总调度
"""
import subprocess, sys, os, time, argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from db_utils import ensure_table, get_pit_dates

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

SCRIPTS = [
    "EC_欧线期货收盘价.py",
    "EC_欧线期货持仓量.py",
    "EC_欧线期货持仓量变化.py",
    "EC_欧线期货跨期价差.py",
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--manual', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("[ERR] 非交易日，跳过")
        return

    mode = 'auto' if args.auto else ('manual' if args.manual else 'auto')
    print("=" * 50)
    print(f"EC @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"日期: pub={pub_date} obs={obs_date} mode={mode}")
    print("=" * 50)

    ok_count, fail_count = 0, 0
    for script in SCRIPTS:
        script_path = os.path.join(SCRIPT_DIR, script)
        if not os.path.exists(script_path):
            print(f"[SKIP] {script} not found")
            fail_count += 1
            continue
        print(f">>> {script}...")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            r = subprocess.run(
                [sys.executable, "-X", "utf8=1", script_path, f"--{mode}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding='utf-8', errors='replace',
                timeout=60, cwd=SCRIPT_DIR, env=env
            )
            out = (r.stdout or "").strip()
            if out:
                for line in out.splitlines()[-3:]:
                    print(f"    {line}")
            if r.returncode == 0:
                ok_count += 1
                print(f"[OK] {script} done")
            else:
                fail_count += 1
                print(f"[WARN] {script} exit:{r.returncode}")
        except subprocess.TimeoutExpired:
            fail_count += 1
            print(f"[WARN] {script} TIMEOUT")
        except Exception as e:
            fail_count += 1
            print(f"[ERR] {script} exception: {e}")
        time.sleep(1)

    print("=" * 50)
    print(f"EC完成: {ok_count}/{ok_count + fail_count}")
    print("=" * 50)

if __name__ == "__main__":
    main()
