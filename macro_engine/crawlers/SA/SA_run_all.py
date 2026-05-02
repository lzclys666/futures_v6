#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

SA_run_all.py - 纯碱数据采集总调度

AKShare接口: futures_spot_price(SA现货+基差), futures_main_sina(SA0日行情),

             futures_inventory_em(纯碱库存), get_shfe_rank_table(SA持仓排名)

"""

import os, sys, subprocess, time

from datetime import datetime

# Windows UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")



SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(SCRIPT_DIR)



SCRIPTS = [

    "SA_抓取现货价.py",

    "SA_抓取期货日行情.py",

    "SA_抓取近月合约价.py",

    "SA_抓取次月合约价.py",

    "SA_抓取持仓排名.py",

    "SA_抓取纯碱库存_em.py",

    "SA_抓取仓单.py",

    "SA_抓取厂家库存.py",

    "SA_抓取行业开工率.py",

    "SA_抓取产量.py",

    # SA_抓取有效预报.py - 仓单数据无免费API，合并到 SA_抓取仓单.py

    "SA_计算SA_FG比价.py",

]



def run_script(name):

    path = os.path.join(SCRIPT_DIR, name)

    if not os.path.exists(path):

        print(f"[WARN]  {name} 不存在，跳过")

        return None

    print(f">>> 运行 {name}...")

    try:

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, path, "--auto"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=60, env=env
        )

        out = (r.stdout or "").strip()

        if out:

            for line in out.splitlines()[-4:]:

                print(f"    {line}")

        if r.returncode == 0:

            print(f"[OK] {name} 完成")

            return True

        else:

            err = (r.stderr or "").strip()

            if err and "SystemExit" not in err:

                for line in err.splitlines()[-2:]:

                    print(f"    [WARN] {line}")

            print(f"[WARN]  {name} 执行失败（错误码: {r.returncode}）")

            return False

    except subprocess.TimeoutExpired:

        print(f"[TIMEOUT]  {name} 超时")

        return False

    except Exception as e:

        print(f"[ERR] {name} 异常: {e}")

        return False



def main():

    print("=" * 50)

    print(f"开始执行 SA 纯碱数据采集任务 @ {datetime.now()}")

    print(f"待执行脚本数: {len(SCRIPTS)}")

    print("=" * 50)

    t0 = time.time()

    ok, fail = 0, 0

    for s in SCRIPTS:

        r = run_script(s)

        if r: ok += 1

        else: fail += 1

        time.sleep(1)

    dt = time.time() - t0

    print("=" * 50)

    print(f"SA 数据采集完成 @ {datetime.now()}")

    print(f"耗时: {dt:.1f} 秒  成功: {ok}/{ok+fail}")

    if fail:

        print(f"失败 {fail} 个")

    else:

        print("[OK] 全部成功")

    print("=" * 50)



if __name__ == "__main__":

    main()

