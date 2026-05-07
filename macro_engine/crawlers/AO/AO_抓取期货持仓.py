#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_抓取期货持仓.py
因子: AO_POS_OI = 上期所氧化铝期货持仓量（手）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare get_shfe_rank_table() 获取交易所排名数据
- L2: 新浪 nf_AO0 实时行情
- L3: save_l4_fallback() 兜底
- bounds: [0, 500000]手

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak
from common.web_utils import fetch_url

FACTOR_CODE = "AO_POS_OI"
SYMBOL = "AO"
BOUNDS = (0, 500_000)


def fetch(obs_date):
    # L1: AKShare 交易所排名
    try:
        print("[L1] AKShare get_shfe_rank_table...")
        import pandas as pd
        # 尝试obs_date，如果非交易日则回退
        for offset in range(0, 7):
            try_date = obs_date - __import__("datetime").timedelta(days=offset)
            result = ak.get_shfe_rank_table(date=try_date.strftime("%Y%m%d"))
            if isinstance(result, dict) and len(result) > 0:
                ao_total = 0
                for contract, df in result.items():
                    if isinstance(df, pd.DataFrame) and "variety" in df.columns:
                        ao_df = df[df["variety"] == "AO"]
                        if len(ao_df) > 0:
                            for col in ao_df.columns:
                                # 总持仓量取long_open_interest（买卖对称）
                                if col == "long_open_interest":
                                    ao_total += float(ao_df[col].sum())
                if ao_total > 0 and BOUNDS[0] <= ao_total <= BOUNDS[1]:
                    print(f"[L1] 成功: {ao_total:.0f} 手 (date={try_date})")
                    return ao_total, "akshare", 1.0
                elif ao_total > 0:
                    print(f"[L1] AO持仓={ao_total:.0f} 超出bounds")
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 新浪
    try:
        print("[L2] 新浪 nf_AO0...")
        html, err = fetch_url("http://hq.sinajs.cn/list=nf_AO0", timeout=10)
        if not err and '"' in html:
            data = html.split('"')[1].split(",")
            if len(data) >= 13:
                oi = float(data[13]) if data[13] else 0
                if oi > 0 and BOUNDS[0] <= oi <= BOUNDS[1]:
                    print(f"[L2] 成功: {oi:.0f} 手")
                    return oi, "sina", 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    value, source, confidence = fetch(obs_date)

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={value} 写入成功")
        return

    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="(持仓量)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")


if __name__ == "__main__":
    main()
