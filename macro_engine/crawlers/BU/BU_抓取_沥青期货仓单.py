#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期货仓单.py
因子: BU_STK_WARRANT = 沥青期货仓单（万吨）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: AKShare futures_shfe_warehouse_receipt() → JSON解析失败（SHFE网站改版，API返回非JSON）
- L2: 尝试SHFE官网直接爬取 → 404（网站改版后所有数据接口失效）
- L3: save_l4_fallback() 兜底（仅当db有历史值时写入）
- 不写占位符

订阅优先级: ★★★
替代付费源: 上期所官网 / Wind / 隆众资讯
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_l4_fallback, get_pit_dates

import akshare as ak

FACTOR_CODE = "BU_STK_WARRANT"
SYMBOL = "BU"


def main():
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); return 0

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1: 尝试SHFE仓单API
    print("[L1] AKShare futures_shfe_warehouse_receipt()...")
    try:
        df = ak.futures_shfe_warehouse_receipt()
        if df is not None and not df.empty:
            print(f"[L1] 获取到{len(df)}行数据，需验证是否包含BU")
            # 如果有BU数据则写入
            if '品种' in df.columns:
                bu_df = df[df['品种'] == 'BU']
                if not bu_df.empty:
                    print(f"[L1] BU仓单数据: {len(bu_df)}行")
                    # TODO: 解析并写入
                    return 0
        print("[L1] SHFE仓单API无BU数据或解析失败")
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: SHFE官网直接爬取
    print("[L2] SHFE官网仓单接口...")
    try:
        from common.web_utils import fetch_url
        html, err = fetch_url("https://www.shfe.com.cn/statements/dataview.html?paramid=delaymarket_ware", timeout=10)
        if err:
            raise ValueError(err)
        if 'BU' in html or '沥青' in html:
            print("[L2] SHFE页面包含BU数据，需进一步解析")
        else:
            print("[L2] SHFE页面无BU仓单数据")
    except Exception as e:
        print(f"[L2] 失败: {e}")

    # L3: save_l4_fallback
    if not save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青仓单)"):
        print(f"[SKIP] {FACTOR_CODE} 无免费数据源，不写占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
