#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_美国非农.py
因子: AU_US_NFP = 美国新增非农就业人数（万人）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare macro_usa_non_farm()，source_confidence=1.0
- L2: FRED PAYEMS（非农就业人数序列，source_confidence=0.9）
- L3: save_l4_fallback() 兜底
- bounds: [-5000.0, 5000.0]万（正常区间约-50到+50万）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from common.web_utils import fetch_url
from datetime import datetime
import warnings

FACTOR_CODE = "AU_US_NFP"
SYMBOL = "AU"
BOUNDS = (-5000.0, 5000.0)


def fetch():
    """L1: AKShare 美国新增非农就业人数（BLS via AKShare）"""
    print("[L1] AKShare macro_usa_non_farm()...")
    warnings.filterwarnings('ignore')
    import akshare as ak
    df = ak.macro_usa_non_farm()
    if df is None or df.empty:
        raise ValueError("no data")
    df = df[df["今值"].notna()]
    if df.empty:
        raise ValueError("all NFP values are NaN")
    df = df.sort_values("日期", ascending=False)
    latest = df.iloc[0]
    raw_value = float(latest["今值"])
    obs_date_str = str(latest["日期"])[:10]
    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d").date()
    print(f"[L1] NFP={raw_value}万 obs={obs_date}")
    return raw_value, obs_date


def fetch_l2():
    """L2: FRED PAYEMS - 全部非农就业人数，需计算新增"""
    print("[L2] FRED PAYEMS...")
    warnings.filterwarnings('ignore')
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=PAYEMS&vintage_date={today}"
    r_text, err = fetch_url(url, timeout=15)
    if err:
        raise ValueError(f"FRED PAYEMS failed: {err}")
    lines = r_text.strip().split("\n")
    valid = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) == 2 and parts[1].strip() not in (".", ""):
            try:
                d = datetime.strptime(parts[0].strip(), "%Y-%m-%d").date()
                v = float(parts[1].strip())
                valid.append((d, v))
            except (ValueError, IndexError):
                pass
    if len(valid) < 2:
        raise ValueError("FRED PAYEMS: not enough data")
    valid.sort(key=lambda x: x[0])
    # 新增 = 最新值 - 上月值
    latest_val = valid[-1][1]
    prev_val = valid[-2][1]
    # 非农新增（万人）= (最新 - 上月) / 1000（单位转换）
    nfp_change = (latest_val - prev_val) / 1000.0
    obs_date = valid[-1][0]
    print(f"[L2] PAYEMS change={nfp_change:.2f}万 obs={obs_date}")
    return nfp_change, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    raw_value, data_obs_date = None, None

    # L1
    try:
        raw_value, data_obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2
    if raw_value is None:
        try:
            raw_value, data_obs_date = fetch_l2()
        except Exception as e:
            print(f"[L2] 失败: {e}")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(美国非农)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
            print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
        return

    # bounds校验
    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(美国非农)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="BLS via AKShare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value}万 obs={data_obs_date}")


if __name__ == "__main__":
    main()
