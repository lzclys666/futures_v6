# -*- coding: utf-8 -*-
"""
CU_run_all.py - 沪铜日度数据采集总调度
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
    ("CU_抓取库存.py",       "CU_INV_SHFE"),
    ("CU_抓取SHFE仓单.py",    "CU_WRT_SHFE"),
    ("CU_计算基差.py",        "CU_SPD_BASIS"),
    ("CU_抓取期货持仓量.py",   "CU_FUT_OI"),
    ("CU_抓取持仓排名.py",     "CU_POS_NET"),
    ("CU_抓取LME库存.py",     "CU_INV_LME"),
    ("CU_计算近远月价差.py",   "CU_SPD_CONTRACT"),
    ("CU_批次2_手动输入.py",   "BATCH2"),
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
    print("=" * 60)
    print(f"CU沪铜数据采集 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"日期: pub={pub_date} obs={obs_date} mode={mode}")
    print("=" * 60)

    log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}_CU.log")
    ok_count, fail_count = 0, 0

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*60}\nCU Start @ {datetime.now()}\n{'='*60}\n")
        for script, hint in SCRIPTS:
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
                    timeout=120, cwd=SCRIPT_DIR, env=env
                )
                out = (r.stdout or "").strip()
                if out:
                    for line in out.splitlines()[-4:]:
                        print(f"    {line}")
                    log.write(f"\n--- {script} ---\n{out}\n")
                if r.stderr:
                    log.write(f"[stderr] {r.stderr}\n")
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

    print("=" * 60)
    print(f"CU完成: {ok_count}/{ok_count + fail_count} 成功, 耗时见log")
    print("=" * 60)

if __name__ == "__main__":
    main()
