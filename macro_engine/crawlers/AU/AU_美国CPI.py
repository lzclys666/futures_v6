#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_美国CPI.py
因子: AU_US_CPI_YOY = 美国CPI同比增速（%）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare macro_usa_cpi_yoy()，source_confidence=1.0
- L2: FRED CPIAUCSL（CPI同比，source_confidence=0.9）
- L3: save_l4_fallback() 兜底
- bounds: [-2.0, 15.0]%（历史区间）

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

FACTOR_CODE = "AU_US_CPI_YOY"
SYMBOL = "AU"
BOUNDS = (-2.0, 15.0)


def fetch():
    """L1: AKShare 美国CPI同比（BLS via AKShare）"""
    print("[L1] AKShare macro_usa_cpi_yoy()...")
    warnings.filterwarnings('ignore')
    import akshare as ak
    df = ak.macro_usa_cpi_yoy()
    if df is None or df.empty:
        raise ValueError("no data")
    df = df[df["现值"].notna()]
    if df.empty:
        raise ValueError("all CPI values are NaN")
    df = df.sort_values("发布日期", ascending=False)
    latest = df.iloc[0]
    raw_value = float(latest["现值"])
    obs_date_str = str(latest["发布日期"])[:10]
    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d").date()
    print(f"[L1] CPI={raw_value}% obs={obs_date}")
    return raw_value, obs_date


def fetch_l2():
    """L2: FRED CPIAUCSL（CPI同比增速）"""
    print("[L2] FRED CPIAUCSL...")
    warnings.filterwarnings('ignore')
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL&vintage_date={today}"
    r_text, err = fetch_url(url, timeout=15)
    if err:
        raise ValueError(f"FRED CPIAUCSL failed: {err}")
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
        raise ValueError("FRED CPIAUCSL: not enough data")
    valid.sort(key=lambda x: x[0])
    # CPI同比需要计算
    latest = valid[-1]
    prev = valid[-13] if len(valid) >= 13 else valid[0]  # 大约1年前
    if prev[1] == 0:
        raise ValueError("FRED CPIAUCSL: prior value is zero")
    cpi_yoy = ((latest[1] - prev[1]) / prev[1]) * 100.0
    print(f"[L2] CPIAUCSL YoY={cpi_yoy:.2f}% obs={latest[0]}")
    return cpi_yoy, latest[0]


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
                             extra_msg="(美国CPI)"):
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
                             extra_msg="(美国CPI)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="BLS via AKShare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value}% obs={data_obs_date}")


if __name__ == "__main__":
    main()
