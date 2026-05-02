# -*- coding: utf-8 -*-
"""
collect_basis.py
多品种基差采集脚本 (Step 2: basis)

数据源:
  - RB (螺纹钢): 99qh.com 真实现货 (spot_price_qh)
  - JM/RU/ZN/NI: 近月合约结算价作为现货代理 (AKShare futures_zh_daily_sina)

PIT 规范:
  - pub_date: 脚本运行日期
  - obs_date: 数据观测日期（最近的交易日）

输出表: {symbol_lower}_futures_basis
  列: pub_date, obs_date, trade_date, contract, futures_close, spot_price, basis, basis_rate
  注: basis_rate = (spot - futures) / futures * 100

用法:
  python collect_basis.py [--variety JM] [--all-history]
"""

import os
import sys
import sqlite3
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(r"D:\futures_v6\macro_engine")
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import akshare as ak
except ImportError:
    print("[FATAL] AKShare not installed. Run: pip install akshare")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = Path(r"D:\futures_v6\macro_engine\pit_data.db")

# ============================================================
# 品种配置
# ============================================================

VARIETY_CONFIG = {
    "JM": {
        "name": "焦煤",
        "main": "JM2609",
        "near": "JM2605",
        "spot_source": "near_contract",  # 近月合约代理
    },
    "RU": {
        "name": "天然橡胶",
        "main": "RU2609",
        "near": "RU2605",
        "spot_source": "near_contract",
    },
    "RB": {
        "name": "螺纹钢",
        "main": "RB2610",
        "near": "RB2605",
        "spot_source": "99qh",  # 99qh.com 真实现货
        "99qh_name": "螺纹钢",
    },
    "ZN": {
        "name": "沪锌",
        "main": "ZN2607",
        "near": "ZN2605",
        "spot_source": "near_contract",
    },
    "NI": {
        "name": "沪镍",
        "main": "NI2607",
        "near": "NI2605",
        "spot_source": "near_contract",
    },
}


# ============================================================
# 工具函数
# ============================================================

def get_pit_dates():
    """获取 PIT 日期"""
    today = datetime.now()
    pub_date = today.strftime("%Y-%m-%d")
    weekday = today.weekday()
    if weekday == 0:
        obs_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    elif weekday == 6:
        obs_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    else:
        obs_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    return pub_date, obs_date


def get_db_conn():
    return sqlite3.connect(str(DB_PATH), timeout=30)


# ============================================================
# 现货获取: 99qh (RB)
# ============================================================

def _spot_from_99qh(symbol_name: str) -> pd.DataFrame:
    """从 99qh.com 获取 RB 现货+期货日频数据"""
    from akshare.spot.spot_price_qh import (
        __get_item_of_spot_price_qh,
        __get_token_of_spot_price_qh,
    )
    import requests

    symbol_map_df = __get_item_of_spot_price_qh()
    symbol_map = dict(zip(symbol_map_df["name"], symbol_map_df["productId"]))
    token = __get_token_of_spot_price_qh()

    pid = symbol_map[symbol_name]
    url = "https://centerapi.fx168api.com/app/qh/api/spot/trend"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "_pcc": token,
        "Origin": "https://www.99qh.com",
        "Referer": "https://www.99qh.com",
    }
    params = {
        "productId": pid,
        "pageNo": "1",
        "pageSize": "50000",
        "startDate": "",
        "endDate": "2050-01-01",
        "appCategory": "web",
    }
    r = requests.get(url, params=params, headers=headers, timeout=30)
    data = r.json()

    if data.get("code") != 0:
        logger.error(f"99qh API error: code={data.get('code')}, msg={data.get('message')}")
        return pd.DataFrame()

    lst = data["data"]["list"]
    df = pd.DataFrame(lst)
    df = df.rename(columns={"date": "trade_date", "fp": "futures_close", "sp": "spot_price"})
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    for col in ["futures_close", "spot_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ============================================================
# 现货获取: 近月合约 (JM/RU/ZN/NI)
# ============================================================

def _spot_from_near_contract(main_contract: str, near_contract: str) -> pd.DataFrame:
    """
    用近月合约结算价作为现货代理
    返回: trade_date, futures_close, spot_price
    """
    main_df = ak.futures_zh_daily_sina(symbol=main_contract)
    near_df = ak.futures_zh_daily_sina(symbol=near_contract)

    if main_df is None or main_df.empty:
        logger.error(f"Main contract {main_contract}: no data")
        return pd.DataFrame()
    if near_df is None or near_df.empty:
        logger.error(f"Near contract {near_contract}: no data")
        return pd.DataFrame()

    main_df = main_df.copy()
    main_df["trade_date"] = pd.to_datetime(main_df["date"]).dt.strftime("%Y-%m-%d")
    main_df["futures_close"] = pd.to_numeric(main_df["settle"], errors="coerce")

    near_df = near_df.copy()
    near_df["trade_date"] = pd.to_datetime(near_df["date"]).dt.strftime("%Y-%m-%d")
    near_df["spot_price"] = pd.to_numeric(near_df["settle"], errors="coerce")

    merged = main_df[["trade_date", "futures_close"]].merge(
        near_df[["trade_date", "spot_price"]], on="trade_date", how="inner"
    )
    return merged


# ============================================================
# 基差采集
# ============================================================

def collect_basis(symbol: str, all_history: bool = False) -> bool:
    """
    采集 {symbol} 的基差数据
    输出表: {symbol_lower}_futures_basis
    """
    cfg = VARIETY_CONFIG[symbol]
    logger.info(f"=== [{symbol}] 基差采集 ({cfg['name']}, source={cfg['spot_source']}) ===")

    pub_date, obs_date = get_pit_dates()
    logger.info(f"PIT: pub={pub_date}, obs={obs_date}")

    # 获取原始数据
    if cfg["spot_source"] == "99qh":
        raw = _spot_from_99qh(cfg["99qh_name"])
        contract_col = cfg["main"]
    else:
        raw = _spot_from_near_contract(cfg["main"], cfg["near"])
        contract_col = cfg["main"]

    if raw.empty:
        logger.error(f"{symbol}: no price data available")
        return False

    logger.info(f"{symbol}: {len(raw)} rows, {raw['trade_date'].min()} ~ {raw['trade_date'].max()}")

    # 计算基差
    raw = raw.copy()
    raw["contract"] = contract_col
    raw["basis"] = raw["spot_price"] - raw["futures_close"]
    raw["basis_rate"] = (raw["basis"] / raw["futures_close"]) * 100
    # PIT: obs_date 必须设为每行对应的历史观测日期 (= trade_date)
    # 否则 load_factor_data 按 obs_date groupby 会把所有历史行坍成一行
    raw["obs_date"] = raw["trade_date"]

    # 过滤异常值
    valid = raw.dropna(subset=["basis_rate"])
    logger.info(
        f"{symbol}: basis_rate mean={valid['basis_rate'].mean():.2f}%, "
        f"std={valid['basis_rate'].std():.2f}%, n={len(valid)}"
    )

    # 写入数据库
    table = f"{symbol.lower()}_futures_basis"
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                pub_date TEXT,
                obs_date TEXT,
                trade_date TEXT,
                contract TEXT,
                futures_close REAL,
                spot_price REAL,
                basis REAL,
                basis_rate REAL,
                PRIMARY KEY (pub_date, contract, trade_date)
            )
        """)
        for _, row in raw.iterrows():
            cur.execute(f"""
                INSERT OR REPLACE INTO {table}
                (pub_date, obs_date, trade_date, contract, futures_close, spot_price, basis, basis_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pub_date, row["obs_date"], row["trade_date"], row["contract"],
                row.get("futures_close"), row.get("spot_price"),
                row.get("basis"), row.get("basis_rate"),
            ))
        conn.commit()
        conn.close()
        logger.info(f"{symbol}: saved {len(raw)} rows -> {table}")
    except Exception as e:
        logger.error(f"{symbol}: DB write failed - {e}")
        return False

    logger.info(f"{symbol}: basis collection DONE OK")
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="多品种基差采集脚本 (Step 2)")
    parser.add_argument(
        "--variety", "-v", nargs="+", default=list(VARIETY_CONFIG.keys()),
        choices=list(VARIETY_CONFIG.keys()),
        help=f"品种列表 (默认全部: {list(VARIETY_CONFIG.keys())})",
    )
    parser.add_argument(
        "--all-history", action="store_true",
        help="采集全部历史数据（默认仅当日增量）",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"多品种基差采集 (Step 2)  品种: {args.variety}")
    logger.info("=" * 60)

    results = {}
    for symbol in args.variety:
        if symbol not in VARIETY_CONFIG:
            logger.error(f"Unknown variety: {symbol}")
            continue
        results[symbol] = collect_basis(symbol, all_history=args.all_history)

    # 汇总
    logger.info("")
    logger.info("=" * 60)
    logger.info("采集汇总")
    logger.info("=" * 60)
    for sym, ok in results.items():
        src = VARIETY_CONFIG[sym]["spot_source"]
        status = "OK" if ok else "FAIL"
        logger.info(f"  {sym} ({VARIETY_CONFIG[sym]['name']}): {status}  source={src}")

    logger.info("=" * 60)
    logger.info("完成")


if __name__ == "__main__":
    main()
