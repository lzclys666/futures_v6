#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算近远月价差
因子: 待定义 = 计算近远月价差

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

SYMBOL = "M"

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === M近远月价差 === obs={obs_date}")
    
    # ----- L1: futures_main_sina -----
    try:
        df = ak.futures_main_sina(symbol="M0")
        if df is not None and len(df) >= 2:
            # 列名中文，用模糊匹配
            close_col = [c for c in df.columns if '收盘' in str(c) or '最新' in str(c) or '最新价' in str(c)]
            if close_col:
                main_close = float(df.iloc[0][close_col[0]])
                near_close = float(df.iloc[1][close_col[0]])
                spread = round(main_close - near_close, 2)
                save_to_db("M_SPD_NEAR_FEAR", SYMBOL, pub_date, obs_date, spread, source_confidence=1.0, source="akshare_futures_main_sina")
                print(f">>> M_SPD_NEAR_FEAR={spread} 写入成功")
                return
    except Exception as e:
        print(f"[L1] futures_main_sina失败: {e}")
    
    # ----- L2: 尝试取次月/远月 -----
    try:
        df = ak.futures_main_sina(symbol="M2")
        if df is not None and len(df) >= 1:
            close_col = [c for c in df.columns if '收盘' in str(c) or '最新' in str(c) or '最新价' in str(c)]
            if close_col:
                far_close = float(df.iloc[0][close_col[0]])
                # 回退主力
                df0 = ak.futures_main_sina(symbol="M0")
                if df0 is not None and len(df0) >= 1:
                    main_close = float(df0.iloc[0][close_col[0]])
                    spread = round(main_close - far_close, 2)
                    save_to_db("M_SPD_NEAR_FEAR", SYMBOL, pub_date, obs_date, spread, source_confidence=0.9, source="akshare_futures_main_sina")
                    print(f">>> M_SPD_NEAR_FEAR={spread} L2成功")
                    return
    except Exception as e:
        print(f"[L2] M2失败: {e}")
    
    # ----- L4: 历史回补 -----
    val = get_latest_value("M_SPD_NEAR_FEAR", SYMBOL)
    if val is not None:
        save_to_db("M_SPD_NEAR_FEAR", SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source="db_回补")
        print(f">>> M_SPD_NEAR_FEAR={val} L4回补成功")
    else:
        print("FAIL: 所有数据源均失败")

if __name__ == "__main__":
    main()
