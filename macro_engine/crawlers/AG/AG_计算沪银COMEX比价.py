#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_计算沪银COMEX比价.py
因子: AG_SPD_SHFE_COMEX = 沪银/COMEX银比价

公式: AG_SPD_SHFE_COMEX = SHFE_AG0收盘价(元/kg) ÷ COMEX_SI0收盘价(元/kg)
    = SHFE_AG0 ÷ (COMEX_SI0_cents_per_oz × 汇率 × 0.321507)

当前状态: [✅正常]
- 数据源: 新浪期货AG0 + 新浪期货SI0 + 新浪USDCNY汇率
- COMEX SI0单位：美分/盎司，需转换为元/千克
- 换算：美分/盎司 × 汇率 × 0.321507 = 元/千克
- bounds: [0.5, 2.0]（沪银/COMEX银比价合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from common.web_utils import fetch_url
import akshare as ak

SYMBOL = "AG"
FACTOR_CODE = "AG_SPD_SHFE_COMEX"
EMIN = 0.5
EMAX = 2.0


def get_close_col(df):
    for c in df.columns:
        if '收盘' in str(c) or '最新' in str(c):
            return c
    return df.columns[-1]


def fetch_usd_cny():
    """获取新浪USDCNY实时汇率"""
    try:
        html, err = fetch_url(
            'https://hq.sinajs.cn/list=USDCNY,USDCNH',
            headers={'Referer': 'https://finance.sina.com.cn'},
            timeout=10
        )
        if err:
            raise Exception(err)
        for line in html.strip().split('\n'):
            if 'USDCNY' in line and 'pv_none' not in line:
                parts = line.split('"')[1].split(',')
                if len(parts) > 1:
                    return float(parts[1])
    except Exception as e:
        print(f"  汇率获取失败: {e}")
    return None


def fetch():
    # L1: 新浪期货AG0 + SI0 + 汇率
    print("[L1] 新浪期货AG0 + SI0 + USDCNY汇率...")
    try:
        ag_df = ak.futures_main_sina("AG0")
        si_df = ak.futures_main_sina("SI0")
        rate = fetch_usd_cny()

        if ag_df is None or len(ag_df) == 0:
            raise ValueError("AG0无数据")
        if si_df is None or len(si_df) == 0:
            raise ValueError("SI0无数据")
        if rate is None:
            raise ValueError("汇率获取失败")

        ag_close = float(ag_df.iloc[-1][get_close_col(ag_df)])
        print(f"  沪银AG: {ag_close} 元/kg")

        si_close = float(si_df.iloc[-1][get_close_col(si_df)])
        # COMEX SI单位：美分/盎司 → 元/千克
        si_cny_kg = si_close * rate * 0.321507
        print(f"  COMEX SI: {si_close} 美分/oz = {si_cny_kg:.2f} 元/kg (汇率={rate})")

        if ag_close <= 0 or si_cny_kg <= 0:
            raise ValueError(f"价格异常: AG={ag_close}, SI_CNY={si_cny_kg}")

        ratio = round(ag_close / si_cny_kg, 4)
        print(f"  比价: {ag_close} / {si_cny_kg:.2f} = {ratio}")

        if not (EMIN <= ratio <= EMAX):
            print(f"[WARN] 比价{ratio}超出bounds[{EMIN},{EMAX}]")
            return None, None

        return ratio, None  # 期货日频，使用obs_date
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备源（需要新浪期货+汇率组合）
    print("[L2] 无备源")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, _ = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="sina_期货AG0_SI0+新浪汇率")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")

    # L3: 兜底保障
    if val is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沪银COMEX比价)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source_confidence=0.0, source="all_sources_failed")
            print(f"[DB] {FACTOR_CODE} NULL占位写入")


if __name__ == "__main__":
    main()
