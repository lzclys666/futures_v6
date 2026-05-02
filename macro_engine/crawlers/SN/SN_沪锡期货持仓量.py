#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪锡期货持仓量
因子: 待定义 = 沪锡期货持仓量

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date
import pandas as pd

FCODE = "SN_FUT_OI"
SYM = "SN"
EMIN = 50000
EMAX = 500000

print("DEBUG: starting SN_FUT_OI")

try:
    df = ak.futures_main_sina(symbol="SN0")
    print("DEBUG: got df", df.shape)
    latest = df.sort_values('日期').iloc[-1]
    print("DEBUG: latest", dict(latest))
    oi_val = float(latest.get('持仓量', 0))
    obs = pd.to_datetime(latest['日期']).date()
    print("DEBUG: oi_val=%s obs=%s" % (oi_val, obs))
    save_to_db(FCODE, SYM, date.today(), obs, oi_val, source_confidence=1.0)
    print("[OK] %s=%s obs=%s" % (FCODE, oi_val, obs))
except Exception as e:
    import traceback
    print("DEBUG: Exception:", type(e).__name__, e)
    traceback.print_exc()
