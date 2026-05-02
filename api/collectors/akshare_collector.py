"""
AKShare 数据源采集器
=====================
封装 AKShare 常用接口，统一返回 DataFrame

注意：
- AKShare 是免费开源数据源，无需 token
- 部分接口有访问频率限制
- 错误处理采用 try-except 捕获具体异常
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime


def collect_akshare(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集 AKShare 数据
    
    Args:
        factor: 因子配置，包含 api_params 等
        
    Returns:
        采集到的数据 DataFrame
        
    Raises:
        Exception: 采集失败时抛出异常
    """
    api_params = factor.get("api_params", {})
    function_name = api_params.get("function")
    
    if not function_name:
        raise ValueError("api_params.function 未指定")
    
    # 获取 AKShare 函数
    if not hasattr(ak, function_name):
        raise ValueError(f"AKShare 不存在函数: {function_name}")
    
    func = getattr(ak, function_name)
    
    # 准备参数（移除 function 字段）
    params = {k: v for k, v in api_params.items() if k != "function"}
    
    # 调用函数
    try:
        df = func(**params)
    except Exception as e:
        raise Exception(f"AKShare.{function_name}() 调用失败: {str(e)}")
    
    # 数据验证
    if df is None or df.empty:
        raise Exception(f"AKShare.{function_name}() 返回空数据")
    
    # 列名标准化（可选）
    df = _normalize_columns(df, factor)
    
    # PIT 处理（如果需要）
    pit_config = factor.get("pit_requirement", {})
    if pit_config.get("need_pit", False):
        df = _add_observation_date(df, pit_config)
    
    return df


def _normalize_columns(df: pd.DataFrame, factor: Dict[str, Any]) -> pd.DataFrame:
    """标准化列名
    
    Args:
        df: 原始 DataFrame
        factor: 因子配置
        
    Returns:
        列名标准化后的 DataFrame
    """
    output_config = factor.get("output_config", {})
    expected_columns = output_config.get("columns")
    
    if expected_columns and len(expected_columns) == len(df.columns):
        df.columns = expected_columns
    
    return df


def _add_observation_date(df: pd.DataFrame, pit_config: Dict[str, Any]) -> pd.DataFrame:
    """添加观测日期（PIT 数据）
    
    注意：AKShare 的历史数据通常没有明确的发布日期
    实际生产中需要配合数据发布日历或爬取公告日期
    
    Args:
        df: 原始 DataFrame
        pit_config: PIT 配置
        
    Returns:
        添加 obs_date 列的 DataFrame
    """
    # 简化处理：用当前日期作为观测日期
    # 实际生产中应该查询数据发布日历
    df["obs_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return df


# ============ 常用 AKShare 接口封装 ============

def get_futures_daily(symbol: str, exchange: str = "shfe", 
                      start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """获取期货日线数据
    
    Args:
        symbol: 品种代码（如 ru, rb）
        exchange: 交易所（shfe, dce, czce, cffex, ine）
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        
    Returns:
        日线数据 DataFrame
    """
    try:
        df = ak.futures_main_sina(symbol=symbol, exchange=exchange)
        
        # 日期过滤
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]
        
        return df
    except Exception as e:
        raise Exception(f"获取期货日线数据失败: {str(e)}")


def get_futures_inventory(symbol: str, exchange: str = "shfe") -> pd.DataFrame:
    """获取期货仓单数据
    
    Args:
        symbol: 品种代码
        exchange: 交易所
        
    Returns:
        仓单数据 DataFrame
    """
    try:
        df = ak.get_cffex_daily()
        return df
    except Exception as e:
        raise Exception(f"获取仓单数据失败: {str(e)}")


# ============ 接口函数注册表 ============
# 用于动态查找对应的采集函数

FUNCTION_MAP = {
    "futures_main_sina": get_futures_daily,
    "futures_comm_info_by_sina": get_futures_daily,
    # 可以继续添加其他常用接口的封装
}
