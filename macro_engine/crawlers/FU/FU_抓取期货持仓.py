#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_抓取期货持仓.py
因子: FU_NET_POSITION = 上期所燃料油前20会员净持仓（手）

公式: 数据采集（无独立计算公式）

当前状态: [OK]正常
- L1: AKShare get_shfe_rank_table（SHFE持仓排行）
- L2: SHFE官网直接爬取
- L3: 备用
- L4: DB回补
- L5: NULL占位

订阅优先级: 无（免费源）
替代付费源: 无
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
import akshare as ak
from common.web_utils import fetch_url
import pandas as pd
import re
from datetime import datetime, timedelta

FACTOR_CODE = "FU_NET_POSITION"
SYMBOL = "FU"
BOUNDS = (-200000, 200000)  # 净持仓 -20万~20万手


def fetch_shfe_rank_ak():
    """L1: AKShare get_shfe_rank_table"""
    try:
        for days_back in range(7):
            check_date = datetime.now() - timedelta(days=days_back)
            # 跳过周末
            if check_date.weekday() >= 5:
                continue
            date_str = check_date.strftime("%Y%m%d")
            try:
                result = ak.get_shfe_rank_table(date=date_str)
                if not isinstance(result, dict) or len(result) == 0:
                    continue
                # 合并所有FU合约的净持仓
                total_long = 0.0
                total_short = 0.0
                found = False
                for key, df in result.items():
                    if not isinstance(df, pd.DataFrame) or len(df) == 0:
                        continue
                    if 'variety' not in df.columns:
                        continue
                    fu_df = df[df['variety'] == 'FU']
                    if len(fu_df) == 0:
                        continue
                    # AKShare 1.18.54 英文列名: long_open_interest / short_open_interest
                    long_col = 'long_open_interest' if 'long_open_interest' in fu_df.columns else None
                    short_col = 'short_open_interest' if 'short_open_interest' in fu_df.columns else None
                    # 兼容旧版中文列名
                    if not long_col:
                        for c in fu_df.columns:
                            if '多' in str(c) and '仓' in str(c):
                                long_col = c
                                break
                    if not short_col:
                        for c in fu_df.columns:
                            if '空' in str(c) and '仓' in str(c):
                                short_col = c
                                break
                    if long_col and short_col:
                        total_long += pd.to_numeric(fu_df[long_col], errors='coerce').sum()
                        total_short += pd.to_numeric(fu_df[short_col], errors='coerce').sum()
                        found = True
                if found and total_long + total_short > 0:
                    net_pos = float(total_long - total_short)
                    print(f"[L1] SHFE持仓({date_str}): FU 多={total_long:.0f} 空={total_short:.0f} 净={net_pos:.0f}")
                    return net_pos, date_str
            except Exception as inner_e:
                err_str = str(inner_e)
                if '非交易日' not in err_str:
                    print(f"[L1] {date_str}: {err_str[:80]}")
                continue
    except Exception as e:
        print(f"[L1] AKShare失败: {e}")
    return None, None


def fetch_shfe_rank_direct():
    """L2: 直接爬取SHFE官网持仓排行"""
    today = datetime.now().strftime("%Y%m%d")
    url = f"http://www.shfe.com.cn/data/delay/RankDetail_{today}.js"
    text, err = fetch_url(url, encoding='utf-8', timeout=15)
    if err:
        print(f"[L2] SHFE直爬失败: {err}")
        return None, None
    try:
        match = re.search(r'"variety"\s*:\s*"FU"[^}]+', text)
        if match:
            fu_text = match.group()
            long_m = re.search(r'"long_position"\s*:\s*([\d.]+)', fu_text)
            short_m = re.search(r'"short_position"\s*:\s*([\d.]+)', fu_text)
            if long_m and short_m:
                net_pos = float(long_m.group(1)) - float(short_m.group(1))
                print(f"[L2] SHFE直爬: 净持仓={net_pos}")
                return net_pos, today
    except Exception as e:
        print(f"[L2] SHFE解析失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    val, source = None, None

    # L1
    val, source = fetch_shfe_rank_ak()
    if val is not None:
        if not (BOUNDS[0] <= val <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                        source_confidence=1.0, source=f"L1-AKShare-SHFE:{source}")
            return

    # L2
    val, source = fetch_shfe_rank_direct()
    if val is not None:
        if not (BOUNDS[0] <= val <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                        source_confidence=0.9, source=f"L2-SHFE官网:{source}")
            return

    # L4: DB fallback
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
        return

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效，不写占位符")


if __name__ == "__main__":
    main()
