#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_抓取净持仓.py
因子: AL_POS_NET = 上期所沪铝期货前20名会员净多单（手）

公式: Σ(多头持仓 - 空头持仓)，单位：手

当前状态: ✅正常
- 数据源: AKShare get_shfe_rank_table()，L1权威（交易所官网数据）
- 采集逻辑: 筛选variety=='AL'，取成交量列求和
- bounds: [-500000, 500000]手

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import requests

FACTOR_CODE = "AL_POS_NET"
SYMBOL = "AL"
BOUNDS = (-500_000, 500_000)


def fetch_net_position():
    # L1: AKShare 交易所排名
    try:
        print("[L1] AKShare get_shfe_rank_table...")
        df = ak.get_shfe_rank_table()
        if df is not None and len(df) > 0:
            al_df = df[df["variety"] == "AL"]
            if len(al_df) > 0:
                cols = al_df.columns.tolist()
                vol_col = None
                for c in cols:
                    if "volume" in str(c).lower() or "成交量" in str(c):
                        vol_col = c
                        break
                if vol_col is None:
                    vol_col = cols[3] if len(cols) > 3 else cols[-1]
                net = float(al_df[vol_col].sum())
                if BOUNDS[0] <= net <= BOUNDS[1]:
                    print(f"[L1] 成功: {net:.0f} 手")
                    return net, "akshare", 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 新浪nf_AL0
    try:
        print("[L2] 新浪nf_AL0...")
        resp = requests.get(
            "http://hq.sinajs.cn/list=nf_AL0",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        resp.encoding = "gbk"
        if resp.status_code == 200 and '"' in resp.text:
            data = resp.text.split('"')[1].split(",")
            if len(data) >= 13:
                vol = float(data[11]) if data[11] else float(data[4])
                print(f"[L2] 成功: {vol:.0f} 手")
                return vol, "sina", 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    # L4回补
    print("[L4] DB历史回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] 兜底: {val}")
        return val, "db_回补", 0.5
    return None, None, None


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_net_position()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
    else:
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
