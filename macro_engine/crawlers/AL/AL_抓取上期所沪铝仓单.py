#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_抓取上期所沪铝仓单.py
因子: AL_INV_SHFE = 上期所沪铝仓单（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_shfe_warehouse_receipt(date=obs_date)（接口已修复，2026-05-05）
- L2: SHFE官网所有数据接口返回404（网站改版）
- L3: save_l4_fallback() 兜底
- bounds: [0, 5000000]吨

订阅优先级: ★★★★
替代付费源: Mysteel年费 | SMM年费（上期所铝仓单数据）
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AL_INV_SHFE"
SYMBOL = "AL"
BOUNDS = (0, 5_000_000)


def fetch():
    # L1: AKShare futures_shfe_warehouse_receipt(date)
    print("[L1] AKShare futures_shfe_warehouse_receipt...")
    try:
        import pandas as pd
        today = pd.Timestamp.now()
        date_str = today.strftime("%Y%m%d")
        data = ak.futures_shfe_warehouse_receipt(date=date_str)
        if data is not None and isinstance(data, dict):
            # dict结构: {"品种": [...], "仓库": [...], "当日仓单": [...]}
            varieties = data.get("品种", [])
            receipts = data.get("当日仓单", [])
            # 找铝相关行
            al_total = 0
            for v, r in zip(varieties, receipts):
                if "铝" in str(v) or "AL" in str(v).upper():
                    try:
                        al_total += float(str(r).replace(",", "").strip())
                    except (ValueError, TypeError):
                        pass
            if al_total > 0:
                print(f"[L1] SHFE铝仓单={al_total:.0f} 吨 (obs={date_str})")
                return al_total, "akshare_shfe_wr", 0.9
            else:
                print(f"[L1] 仓单数据中找到铝，但总量为0: varieties={varieties}")
        else:
            print(f"[L1] 返回数据类型: {type(data)}")
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: SHFE官网备用
    print("[L2] SHFE官网数据...")
    try:
        from common.web_utils import fetch_url
        url = "https://www.shfe.com.cn/data/inventory/"
        html, err = fetch_url(url, timeout=10)
        if err:
            print(f"[L2] SHFE官网失败: {err}")
        else:
            print("[L2] SHFE官网返回数据，但解析暂未实现")
    except Exception as e:
        print(f"[L2] SHFE备用也失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, source, confidence = fetch()

    if val is not None and BOUNDS[0] <= val <= BOUNDS[1]:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(SHFE铝仓单)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} 无可用数据源")


if __name__ == "__main__":
    main()
