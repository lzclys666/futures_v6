#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取持仓量
因子: XX_XXXXX = 抓取持仓量

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
FACTOR_CODE = "XX_XXXXX"  # 必须与 config/factors/{SYMBOL}/ 下的YAML文件名一致
SYMBOL = "XX"             # 品种代码，如 "JM", "RB", "AL"
FACTOR_NAME = "因子名称"   # 如 "焦煤持仓量"
FREQ = "日频"             # 日频/周频/月频

# 数据源配置（按L1L2L3优先级）
SOURCE_PRIMARY = "AKShare xxx"      # L1免费权威
SOURCE_BACKUP = "AKShare yyy"       # L1第二选择或L2免费聚合
SOURCE_PAID = ""                    # L3付费源（如有）

# 阈值配置（动态标定，每月校准）
MIN_VALUE = 0           # 物理下限
MAX_VALUE = 1000000     # 物理上限

# DB兜底过期天数
MAX_STALENESS_DAYS = 30 if FREQ == "日频" else (7 if FREQ == "周频" else 90)

"""
【配置区结束】
"""

# ========== 标准导入（无需修改）==========
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import datetime
import traceback

# ========== 输出分级系统（无需修改）==========
# --quiet : 只输出一行结果（run_all汇总模式）
# --debug : 输出所有详细信息（调试模式）
# 默认    : 输出关键节点信息

_DEBUG = "--debug" in sys.argv
_QUIET = "--quiet" in sys.argv


def log_info(msg):
    """关键信息（默认+debug均输出）"""
    if not _QUIET:
        print(msg)


def log_debug(msg):
    """详细信息（仅debug模式）"""
    if _DEBUG:
        print(f"[DEBUG] {msg}")


def log_result(msg):
    """最终结果（所有模式都输出）"""
    print(msg)


# ========== 数据获取函数（必须实现）==========
def fetch_data():
    """
    四级降级获取数据
    返回: (value, source_label, confidence) 或 (None, None, None)
    
    source_label: "primary" | "backup" | "database" | "manual"
    confidence: 1.0 | 0.9 | 0.6 | 0.5
    """
    
    # ----- 源1：主力源（L1免费权威）-----
    try:
        # TODO: 实现主力源获取逻辑
        # value = ak.xxx_function(...)
        # if value is not None:
        #     log_info(f"[源1] 成功: {value}")
        #     log_debug(f"[源1] 原始数据: {raw_df.head()}")
        #     return value, "primary", 1.0
        pass
    except Exception as e:
        log_debug(f"[源1] 失败: {e}")
    
    # ----- 源2：备用源（L1第二选择或L2免费聚合）-----
    try:
        # TODO: 实现备用源获取逻辑
        pass
    except Exception as e:
        log_debug(f"[源2] 失败: {e}")
    
    # ----- 源3：DB历史最新值（月频/付费因子保留，日/周频可选去掉）-----
    if FREQ in ("月频",) or SOURCE_PAID:  # 月频或纯付费因子保留Source 3
        try:
            val = get_latest_value(FACTOR_CODE, SYMBOL)
            if val is not None:
                log_info(f"[源3] DB兜底: {val}")
                return val, "database", 0.6
        except Exception as e:
            log_debug(f"[源3] 失败: {e}")
    
    # ----- 源4：手动输入（--auto模式跳过）-----
    if "--auto" not in sys.argv:
        try:
            val = input(f"请输入 {FACTOR_CODE}: ").strip()
            if val:
                return float(val), "manual", 0.5
        except Exception as e:
            log_debug(f"[源4] 输入失败: {e}")
    
    log_debug("[失败] 所有数据源均失败")
    return None, None, None


# ========== 主程序（无需修改）==========
if __name__ == "__main__":
    # 非交易日判断
    pub_date, obs_date = get_pit_dates(freq=FREQ)
    if pub_date is None:
        if _QUIET:
            print(f"{FACTOR_CODE}: SKIP(非交易日)")
        else:
            print("非交易日，跳过")
        exit(0)
    
    ensure_table()
    log_info(f"=== {FACTOR_CODE} ({FACTOR_NAME}) ===")
    log_info(f"发布日期: {pub_date} | 观测日期: {obs_date}")
    
    value, source, confidence = fetch_data()
    
    if value is not None:
        # 合理性校验
        if not (MIN_VALUE <= value <= MAX_VALUE):
            log_result(f"{FACTOR_CODE}: {value} FAIL(超出范围{MIN_VALUE}~{MAX_VALUE})")
            exit(1)
        
        # 写入数据库
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, 
                   source_confidence=confidence, source=source)
        log_result(f"{FACTOR_CODE}: {value} OK")
    else:
        log_result(f"{FACTOR_CODE}: FAIL")
        exit(1)