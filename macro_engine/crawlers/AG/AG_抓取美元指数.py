#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取美元指数.py
因子: AG_MACRO_DXY = 美元指数（DXY）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: FRED DTWEXBGS（广义美元指数）成功获取
- L2: FRED DTWEXM（名义有效汇率）备用
- 注：DTWEXBGS与ICE DXY不同，但可作为宏观美元参考
- L1: FRED DTWEXBGS（广义美元指数）作为DXY替代
- L2: FRED DTWEXM（名义有效汇率）备用
- L3: save_l4_fallback() 也无历史数据
- 注意：DTWEXBGS与ICE DXY不同，但可作为宏观美元参考

订阅优先级: ★★★
替代付费源: FRED API Key（免费注册）/ Wind / Bloomberg
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from common.web_utils import fetch_url
from datetime import datetime

FACTOR_CODE = "AG_MACRO_DXY"
SYMBOL = "AG"
EMIN = 90.0
EMAX = 130.0


def fetch_fred_csv(series_id):
    """从FRED CSV获取最新观测值"""
    today = datetime.now().strftime('%Y-%m-%d')
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&vintage_date={today}'
    try:
        html, err = fetch_url(url, timeout=15)
        if err:
            return None, None
        lines = html.strip().split('\n')
        if len(lines) < 2:
            return None, None
        for line in reversed(lines[1:]):
            parts = line.split(',')
            if len(parts) == 2 and parts[1].strip() not in ('.', ''):
                date_str = parts[0].strip()
                val = float(parts[1].strip())
                return val, datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception as e:
        print(f"[{series_id}] 失败: {e}")
    return None, None


def fetch():
    # L1: FRED DTWEXBGS（广义美元指数）
    print("[L1] FRED DTWEXBGS（广义美元指数）...")
    val, obs = fetch_fred_csv('DTWEXBGS')
    if val is not None:
        print(f"[L1] DTWEXBGS={val:.4f} obs={obs}")
        if not (EMIN <= val <= EMAX):
            print(f"[WARN] DTWEXBGS={val} 超出bounds[{EMIN},{EMAX}]")
            val = None
            obs = None
    else:
        print("[L1] DTWEXBGS 获取失败")

    # L2: FRED DTWEXM（名义有效汇率）
    if val is None:
        print("[L2] FRED DTWEXM（名义有效汇率）备用...")
        val2, obs2 = fetch_fred_csv('DTWEXM')
        if val2 is not None:
            print(f"[L2] DTWEXM={val2:.4f} obs={obs2}")
            if EMIN <= val2 <= EMAX:
                val = val2
                obs = obs2
            else:
                print(f"[WARN] DTWEXM={val2} 超出bounds[{EMIN},{EMAX}]")
                val = None
                obs = None
        else:
            print("[L2] DTWEXM 也获取失败")

    return val, obs


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, data_obs = fetch()

    if val is not None:
        write_obs = data_obs if data_obs else obs_date
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, write_obs, val,
                   source_confidence=0.9, source="FRED_DTWEXBGS")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(美元指数)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} ⛔永久跳过（无免费源: FRED API Key/彭博）")


if __name__ == "__main__":
    main()
