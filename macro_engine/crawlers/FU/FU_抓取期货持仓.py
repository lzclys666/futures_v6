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
        # 尝试最近5个交易日
        for days_back in range(5):
            check_date = datetime.now() - timedelta(days=days_back)
            date_str = check_date.strftime("%Y%m%d")
            try:
                result = ak.get_shfe_rank_table(date=date_str)
                if result is None or not result:
                    continue
                # result是dict，key为品种名
                # 找FU相关的合约
                for key, df in result.items():
                    if 'fu' in str(key).lower() or 'FU' in str(key):
                        if isinstance(df, pd.DataFrame) and len(df) > 0:
                            # 计算前20净持仓：多头持仓 - 空头持仓
                            col_map = {str(c).strip(): c for c in df.columns}
                            long_col = col_map.get('多头持仓', None)
                            short_col = col_map.get('空头持仓', None)
                            if long_col and short_col:
                                long_sum = pd.to_numeric(df[long_col], errors='coerce').sum()
                                short_sum = pd.to_numeric(df[short_col], errors='coerce').sum()
                                net_pos = float(long_sum - short_sum)
                                print(f"[L1] SHFE持仓排行({date_str}): {key} 净持仓={net_pos}")
                                return net_pos, date_str
            except Exception as inner_e:
                print(f"[L1] {date_str} 尝试失败: {inner_e}")
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

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效，写入NULL占位")
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                source_confidence=0.0, source="L5-NULL占位")


if __name__ == "__main__":
    main()
