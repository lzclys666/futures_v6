#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_抓取前20净持仓.py
因子: AO_POS_NET = 上期所氧化铝期货前20名会员净多单（手）

公式: Σ(多头持仓 - 空头持仓)，单位：手

当前状态: [✅正常]
- L1: AKShare get_shfe_rank_table()（交易所官网数据，L1权威）
- L2: 新浪 nf_AO0 备用
- L3: save_l4_fallback() 兜底
- bounds: [-500000, 500000]手

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

FACTOR_CODE = "AO_POS_NET"
SYMBOL = "AO"
BOUNDS = (-500_000, 500_000)


def fetch_net_position(obs_date):
    # L1: AKShare 交易所排名
    try:
        print("[L1] AKShare get_shfe_rank_table...")
        import pandas as pd
        # 尝试obs_date，如果非交易日则回退
        for offset in range(0, 7):
            try_date = obs_date - __import__("datetime").timedelta(days=offset)
            result = ak.get_shfe_rank_table(date=try_date.strftime("%Y%m%d"))
            frames = []
            if isinstance(result, dict):
                for contract, df in result.items():
                    if isinstance(df, pd.DataFrame) and "variety" in df.columns:
                        ao_df = df[df["variety"] == "AO"]
                        if len(ao_df) > 0:
                            frames.append(ao_df)
            elif isinstance(result, pd.DataFrame) and "variety" in result.columns:
                ao_df = result[result["variety"] == "AO"]
                if len(ao_df) > 0:
                    frames.append(ao_df)

            if frames:
                combined = pd.concat(frames, ignore_index=True)
                cols = combined.columns.tolist()
                long_col = short_col = None
                for c in cols:
                    cl = str(c).lower()
                    if ("long" in cl or "买" in cl or "多" in cl) and "chg" not in cl:
                        long_col = c
                    elif ("short" in cl or "卖" in cl or "空" in cl) and "chg" not in cl:
                        short_col = c
                if long_col and short_col:
                    ao_long = float(combined[long_col].sum())
                    ao_short = float(combined[short_col].sum())
                    net = ao_long - ao_short
                    if BOUNDS[0] <= net <= BOUNDS[1]:
                        print(f"[L1] 成功: 净持仓={net:.0f} 手 (多={ao_long:.0f}, 空={ao_short:.0f}, date={try_date})")
                        return net, "akshare", 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 新浪
    try:
        print("[L2] 新浪 nf_AO0...")
        html, err = fetch_url("http://hq.sinajs.cn/list=nf_AO0", timeout=10)
        if not err and '"' in html:
            data = html.split('"')[1].split(",")
            if len(data) >= 13:
                vol = float(data[11]) if data[11] else float(data[4])
                if BOUNDS[0] <= vol <= BOUNDS[1]:
                    print(f"[L2] 成功: {vol:.0f} 手")
                    return vol, "sina", 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    value, source, confidence = fetch_net_position(obs_date)

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={value} 写入成功")
        return

    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="(前20净持仓)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")


if __name__ == "__main__":
    main()
