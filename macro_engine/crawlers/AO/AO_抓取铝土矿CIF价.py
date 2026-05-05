#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_抓取铝土矿CIF价.py
因子: AO_PRC_CIF_BAUXITE = 几内亚铝土矿CIF价（美元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [⚠️待修复]
- L1: AKShare 尝试海关进出口价格数据
- L2: 行业新闻/百川盈孚备用
- L3: save_l4_fallback() 兜底
- bounds: [40, 120]美元/吨
- 注: 月度数据，通常滞后1-2个月

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AO_PRC_CIF_BAUXITE"
SYMBOL = "AO"
BOUNDS = (40, 120)  # 美元/吨


def fetch():
    # L1: AKShare 海关价格数据
    print("[L1] AKShare 海关进出口价格数据...")
    try:
        # 尝试获取铝矿砂进口均价
        df = ak.macro_china_imports(index="铝矿砂及其精矿")
        if df is not None and len(df) > 0:
            # 如果有单价列
            for col in ["单价", "均价", "price", "unit_price"]:
                if col in df.columns:
                    val = float(df.iloc[-1][col])
                    if BOUNDS[0] <= val <= BOUNDS[1]:
                        print(f"[L1] 成功: {val:.2f} 美元/吨")
                        return val, "akshare_customs", 0.9
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 备用
    print("[L2] 行业新闻备用...")
    try:
        # 尝试从行业网站获取
        from common.web_utils import fetch_url
        html, err = fetch_url("https://www.smm.cn", timeout=10)
        if err:
            print(f"[L2] SMM失败: {err}")
        else:
            print("[L2] SMM返回数据，但解析暂未实现")
    except Exception as e:
        print(f"[L2] 失败: {e}")

    return None, None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    val, source, confidence = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source=source, source_confidence=confidence)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="(铝土矿CIF价)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} 无可用数据源")


if __name__ == "__main__":
    main()
