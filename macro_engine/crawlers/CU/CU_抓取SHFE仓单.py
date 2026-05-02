#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取SHFE仓单
因子: CU_WRT_SHFE = 抓取SHFE仓单

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date, timedelta

FACTOR_CODE = "CU_WRT_SHFE"
SYMBOL = "CU"
EXPECTED_MIN = 5000
EXPECTED_MAX = 200000

def try_date(d):
    if d.weekday() >= 5:
        return None
    date_str = d.strftime('%Y%m%d')
    try:
        r = ak.futures_shfe_warehouse_receipt(date=date_str)
        if isinstance(r, dict) and r and '\u94dc' in r:
            return d, r
    except Exception:
        pass
    return None

def prev_month(d):
    y, m = d.year, d.month
    m -= 1
    if m == 0:
        m = 12; y -= 1
    return date(y, m, 15)

def get_last_trading_day_with_data():
    """搜索最近有SHFE铜仓单数据的日期"""
    today = date.today()
    
    # 策略1: 逐日查最近60个交易日
    for days in range(80):
        d = today - timedelta(days=days)
        result = try_date(d)
        if result is not None:
            return result
    
    # 策略2: 按月查，从1年前开始
    cur = date(today.year - 1, today.month, 15)
    end = today - timedelta(days=60)
    while cur < end:
        result = try_date(cur)
        if result is not None:
            return result
        cur = prev_month(cur)
    
    return None, None

def get_wrt_from_cu_df(cu_df):
    """从铜仓单DataFrame中提取总仓单量"""
    # 优先取"完税商品总计"行（第一个非零值）
    rows = cu_df[cu_df['WHABBRNAME'].str.contains('\u5b8c\u7a0d\u5546\u54c1\u603b\u8ba1', na=False)]
    if not rows.empty:
        for _, row in rows.iterrows():
            v = float(row['WRTWGHTS'])
            if v > 0:
                return v
    # 备选: 取"总计"行
    rows = cu_df[cu_df['WHABBRNAME'].str.contains('\u603b\u8ba1', na=False)]
    if not rows.empty:
        for _, row in rows.iterrows():
            v = float(row['WRTWGHTS'])
            if v > 0:
                return v
    # 兜底: 所有行的仓单量之和（排除表头行）
    valid = cu_df[cu_df['WHABBRNAME'].notna() & (cu_df['WHABBRNAME'] != '')]
    return float(valid['WRTWGHTS'].sum())

def fetch():
    result = get_last_trading_day_with_data()
    obs_date, r = result[0], result[1]
    if obs_date is None or r is None:
        raise ValueError("无法获取SHFE仓单日期")
    cu_df = r.get('\u94dc', None)
    if cu_df is None:
        raise ValueError("铜不在仓单数据中")
    wrt = get_wrt_from_cu_df(cu_df)
    return wrt, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1 FAIL] %s: %s" % (FACTOR_CODE, e))
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print("[L4 Fallback] %s=%.2f" % (FACTOR_CODE, latest))
            return
        print("[L4 SKIP] %s: no data" % FACTOR_CODE)
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print("[WARN] %s=%.1f out of [%d,%d]" % (FACTOR_CODE, raw_value, EXPECTED_MIN, EXPECTED_MAX))
        return

    pub_date = date.today()
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
    print("[OK] %s=%.1f obs=%s" % (FACTOR_CODE, raw_value, obs_date))

if __name__ == "__main__":
    main()
