#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_计算SHFE_LME比价.py
因子: AL_SPD_SHFE_LME = SHFE沪铝/伦敦LME铝比价

公式: 比价 = SHFE沪铝主力价(元/吨) / (LME铝价(美元/吨) × 美元人民币汇率)
说明: 跨市套利参考指标，剔除外汇影响后的沪伦铝比值，正常区间0.85~1.15

当前状态: ✅正常
- SHFE铝价: AKShare futures_settle_shfe（每日结算价，L1权威）
- LME铝价: 数据库已有记录AL_LME_PRICE（铝道网爬虫写入，L2聚合）
- 汇率: 实时获取新浪USDCNY（L2），避免硬编码

订阅优先级: ★★（LME价格来自铝道网免费数据）
替代付费源: 无需付费
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value, DB_PATH

import akshare as ak
from common.web_utils import fetch_url
import datetime
import sqlite3

FACTOR_CODE = "AL_SPD_SHFE_LME"
SYMBOL = "AL"
LME_FACTOR_CODE = "AL_LME_PRICE"
FX_FACTOR_CODE = "AL_COST_USDCNY"


def fetch_fx_rate():
    """获取实时美元人民币汇率（L2新浪）"""
    try:
        html, err = fetch_url(
            "http://hq.sinajs.cn/list=USDCNY",
            timeout=10
        )
        if not err and '"' in html:
            val = html.split('"')[1].split(",")[0]
            fx = float(val)
            if 6.0 < fx < 8.0:
                return fx
    except Exception:
        pass
    return None


def fetch_shfe_al_price():
    """获取上期所沪铝主力价格（L1 AKShare）"""
    for i in range(5):
        date_str = (datetime.date.today() - datetime.timedelta(days=i)).strftime("%Y%m%d")
        try:
            df = ak.futures_settle_shfe(date=date_str)
            if df is not None and len(df) > 0:
                al_df = df[df["variety"] == "al"].sort_values("settle_price", ascending=False)
                if len(al_df) > 0:
                    return float(al_df.iloc[0]["settle_price"])
        except Exception:
            continue
    return None


def fetch_lme_price_from_db(obs_date):
    """从数据库获取LME铝价格"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT raw_value FROM pit_factor_observations "
            "WHERE factor_code=? AND obs_date=? "
            "ORDER BY pub_date DESC LIMIT 1",
            (LME_FACTOR_CODE, obs_date)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return float(row[0])
    except Exception:
        pass
    return None


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日")
        exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # 获取三要素
    shfe_price = fetch_shfe_al_price()
    lme_price = fetch_lme_price_from_db(obs_date)
    fx_rate = fetch_fx_rate()

    print(f"  SHFE沪铝: {shfe_price}")
    print(f"  LME铝价:  {lme_price} USD/ton")
    print(f"  美元汇率: {fx_rate}")

    if shfe_price and lme_price and fx_rate:
        ratio = round(shfe_price / (lme_price * fx_rate), 4)
        # bounds校验: 0.5~2.0（正常区间0.85~1.15）
        if 0.5 <= ratio <= 2.0:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, ratio,
                       source="akshare+sina+db", source_confidence=0.85)
            print(f"[OK] AL_SPD_SHFE_LME={ratio} (SHFE={shfe_price}, LME={lme_price}, FX={fx_rate})")
        else:
            print(f"[WARN] 比值{ratio}超出合理范围[0.5,2.0]，跳过写入")
    elif not lme_price:
        # L4回补
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            print(f"[L4] LME价格缺失，DB回补: {val}")
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source="db_回补", source_confidence=0.5)
        else:
            print("[WARN] AL_SPD_SHFE_LME 所有数据源均失败")
    else:
        print("[WARN] SHFE或汇率获取失败，跳过")
