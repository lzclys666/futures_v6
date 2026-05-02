#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取汽车销量
因子: BR_DEM_AUTO = 抓取汽车销量

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, save_to_db
import akshare as ak
import pandas as pd

FACTOR_CODE = "BR_DEM_AUTO"
SYMBOL = "BR"


def main():
    ensure_table()
    from datetime import date
    import calendar, re

    today = date.today()
    pub_date = today.isoformat()

    print(f"(auto) === BR_DEM_AUTO === pub={pub_date}")

    try:
        df = ak.car_market_total_cpca(symbol='狭义乘用车', indicator='销量')
        if df is not None and len(df) > 0:
            df.columns = ['month', 'prev_year', 'curr_year']
            df = df.dropna(subset=['curr_year'])
            if len(df) == 0:
                raise ValueError("无有效数据")
            latest = df.iloc[-1]
            val = float(latest['curr_year'])
            if not (50 < val < 500):
                raise ValueError(f"值超出合理范围: {val}")
            # 从 "2025年12月" 解析出年月
            m = re.search(r'(\d{4})年(\d+)月', str(latest['month']))
            if m:
                year, month = int(m.group(1)), int(m.group(2))
                last_day = calendar.monthrange(year, month)[1]
                obs_date = f"{year}-{month:02d}-{last_day:02d}"
            else:
                # 无法解析则用上月月末
                year, month = today.year, today.month - 1
                if month == 0: year -= 1; month = 12
                obs_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source_confidence=1.0, source="akshare_car_market_total_cpca")
            print(f"✅ BR_DEM_AUTO={val} (obs={obs_date}) 写入成功")
            return 0
    except Exception as e:
        print(f"[L1] 中汽协失败: {e}")
        return 1

    print("[L1] 中汽协数据不可用，BR_DEM_AUTO跳过")
    return 1


if __name__ == '__main__':
    exit(main())
