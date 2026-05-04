#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取SHFE白银仓单.py
因子: AG_INV_SHFE_AG = 上期所白银仓单（吨）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: AKShare futures_shfe_warehouse_receipt() 接口失效（JSON解析错误）
- L2: SHFE官网所有数据接口返回404（网站改版）
- L3: save_l4_fallback() 也无历史数据

订阅优先级: ★★★★（高）
替代付费源: Mysteel年费 | SMM年费（上期所白银仓单数据）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AG_INV_SHFE_AG"
SYMBOL = "AG"


def fetch():
    # L1: AKShare SHFE仓单
    print("[L1] AKShare futures_shfe_warehouse_receipt(symbol='白银')...")
    try:
        df = ak.futures_shfe_warehouse_receipt(symbol='白银')
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row.get('仓单数量', row.get('仓单', 0)))
            print(f"[L1] SHFE白银仓单={val} 吨")
            return val, None
        else:
            print("[L1] 返回空数据")
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: SHFE官网备用
    print("[L2] SHFE官网仓单数据...")
    try:
        # SHFE官网改版后404，尝试备用URL
        from common.web_utils import fetch_url
        url = "https://www.shfe.com.cn/data/inventory/"
        html, err = fetch_url(url, timeout=10)
        if err or not html:
            print(f"[L2] SHFE官网失败: {err}")
        else:
            print("[L2] SHFE官网返回数据，但解析暂未实现")
    except Exception as e:
        print(f"[L2] SHFE备用也失败: {e}")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, _ = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="akshare_shfe_warehouse_receipt")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(SHFE白银仓单)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} ⛔永久跳过（无免费源: Mysteel/SMM）")


if __name__ == "__main__":
    main()
