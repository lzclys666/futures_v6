# -*- coding: utf-8 -*-
"""
补采脚本: 2026-04-30 交易日数据
顺序执行，BACKFILL_DATE 环境变量注入 db_utils.get_pit_dates()
"""
import subprocess
import os
import sys
from datetime import date

OBS_DATE = date(2026, 4, 30)
BASE_DIR = r"D:\futures_v6\macro_engine\crawlers"
PYTHON = "python"

PRODUCTS = [
    'AG', 'AL', 'AO', 'AU', 'BR', 'BU', 'CU', 'EC', 'EG', 'HC',
    'I', 'J', 'JM', 'LC', 'LH', 'M', 'NI', 'NR', 'P', 'PB',
    'PP', 'RB', 'RU', 'SA', 'SC', 'SN', 'TA', 'Y', 'ZN'
]


def run_product(product):
    """运行单个品种的 run_all.py"""
    script = os.path.join(BASE_DIR, product, f"{product}_run_all.py")
    if not os.path.exists(script):
        return product, "SKIP", "script not found"

    env = os.environ.copy()
    env["BACKFILL_DATE"] = OBS_DATE.isoformat()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        proc = subprocess.Popen(
            [PYTHON, "-X", "utf8=1", script, "--auto"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=BASE_DIR,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            stdout, stderr = proc.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return product, "TIMEOUT", "240s exceeded"

        out = stdout.strip()[-200:] if stdout else ""
        err = stderr.strip()[-200:] if stderr else ""
        if proc.returncode == 0:
            lines = [l for l in stdout.strip().split("\n") if l.strip()]
            info = lines[-1][:100] if lines else "success"
            return product, "OK", info
        else:
            return product, "FAIL", (err or out)[-100:]
    except Exception as e:
        return product, "ERROR", str(e)[:100]


def main():
    sep = "=" * 60
    print(sep)
    print(f"补采 {OBS_DATE} 数据 (BACKFILL_DATE={OBS_DATE.isoformat()})")
    print(sep)

    results = {}
    for i, product in enumerate(PRODUCTS, 1):
        product, status, msg = run_product(product)
        results[product] = (status, msg)
        icon = {"OK": "[OK]", "FAIL": "[FAIL]", "TIMEOUT": "[TIMEOUT]", "ERROR": "[ERROR]", "SKIP": "[SKIP]"}.get(status, "[?]")
        print(f"{icon} [{i}/{len(PRODUCTS)}] {product}: {msg[:80]}")
        sys.stdout.flush()

    ok = sum(1 for s, _ in results.values() if s == "OK")
    fail = sum(1 for s, _ in results.values() if s not in ("OK", "SKIP"))
    print(sep)
    print(f"补采完成: {ok}/{len(PRODUCTS)} 成功, {fail} 失败")
    print(sep)
    return ok, fail


if __name__ == "__main__":
    main()
