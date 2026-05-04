#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取现货价.py
因子: AG_SPD_BASIS = 沪银现货价（元/千克）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: AKShare futures_spot_price 对"沪银/白银"返回空或历史数据
- L2: AKShare futures_zh_spot 接口故障（Sina数据格式变更）
- L3: save_l4_fallback() 也无历史数据（之前从未成功采集）
- 注：SGE白银现货 spot_silver_benchmark_sge 返回的是国际银价，非沪银

订阅优先级: ★★★
替代付费源: Mysteel年费 | SMM年费 | 隆众资讯年费
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
import akshare as ak

FACTOR_CODE = "AG_SPD_BASIS"
SYMBOL = "AG"


SYM_ALTERNATIVES = ["沪银", "白银", "AG", "ag", "Silver", "silver"]


def fetch():
    # L1: AKShare futures_spot_price 多名称尝试
    print("[L1] AKShare futures_spot_price...")
    for sym in SYM_ALTERNATIVES:
        try:
            import pandas as pd
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            df = ak.futures_spot_price(symbol=sym, date=today)
            if df is not None and len(df) > 0:
                row = df.iloc[-1]
                val = float(row.get('均价', row.iloc[-1]))
                obs_str = str(row.get('日期', today))[:10]
                print(f"[L1] futures_spot_price(symbol='{sym}') = {val}")
                # 检查是否是当前数据
                if obs_str >= today[:7]:  # 简单判断是否是当月数据
                    return val, obs_str
                else:
                    print(f"[L1] 仅返回历史数据: {obs_str}，非当前")
        except Exception as e:
            print(f"[L1] symbol='{sym}' 失败: {e}")
        continue

    # L2: AKShare futures_zh_spot
    print("[L2] AKShare futures_zh_spot...")
    try:
        df = ak.futures_zh_spot(symbol="AG")
        if df is not None and len(df) > 0:
            print(f"[L2] futures_zh_spot 返回 {len(df)} 行，但数据格式需验证")
            # 该接口已不稳定，跳过
    except Exception as e:
        print(f"[L2] futures_zh_spot 失败: {e}")

    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    val, _ = fetch()

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="akshare_futures_spot")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
        return

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(沪银现货价)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[DB] {FACTOR_CODE} NULL占位写入")
        print(f"[⛔] {FACTOR_CODE} ⛔永久跳过（无免费源: Mysteel/SMM/隆众）")


if __name__ == "__main__":
    main()
