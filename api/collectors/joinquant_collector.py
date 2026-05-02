"""
聚宽 (JoinQuant) 数据源采集器
=============================
封装聚宽 API 接口，统一返回 DataFrame

注意：
- 聚宽是免费量化平台，需要注册账号
- 有访问频率限制（免费用户）
- 支持期货、股票、基金等数据

依赖：
    pip install jqdatasdk
"""

import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
import os


# 聚宽认证信息
JQ_USER = os.getenv("JQ_USER", "")
JQ_PASS = os.getenv("JQ_PASS", "")
_jq_initialized = False


def _ensure_initialized() -> bool:
    """确保聚宽 SDK 初始化
    
    Returns:
        是否初始化成功
    """
    global _jq_initialized
    
    if _jq_initialized:
        return True
    
    try:
        from jqdatasdk import auth
        
        if not JQ_USER or not JQ_PASS:
            raise Exception("聚宽账号未配置，请设置环境变量 JQ_USER 和 JQ_PASS")
        
        auth(JQ_USER, JQ_PASS)
        _jq_initialized = True
        
        return True
        
    except ImportError:
        raise ImportError("jqdatasdk 未安装，请运行：pip install jqdatasdk")
    except Exception as e:
        raise Exception(f"聚宽认证失败：{str(e)}")


def collect_joinquant(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集聚宽数据
    
    Args:
        factor: 因子配置，包含 api_params 等
        
    Returns:
        采集到的数据 DataFrame
        
    Raises:
        Exception: 采集失败时抛出异常
    """
    # 确保初始化
    _ensure_initialized()
    
    api_params = factor.get("api_params", {})
    function_name = api_params.get("function")
    
    if not function_name:
        raise ValueError("api_params.function 未指定")
    
    # 准备参数
    params = {k: v for k, v in api_params.items() if k != "function"}
    
    # 调用聚宽接口
    try:
        if function_name == "get_futures_daily":
            df = _get_futures_daily(params)
        elif function_name == "get_futures_contracts":
            df = _get_futures_contracts(params)
        elif function_name == "get_macro_data":
            df = _get_macro_data(params)
        elif function_name == "get_price":
            df = _get_price(params)
        else:
            raise ValueError(f"不支持的聚宽接口：{function_name}")
        
    except Exception as e:
        raise Exception(f"聚宽.{function_name}() 调用失败：{str(e)}")
    
    # 数据验证
    if df is None or df.empty:
        raise Exception(f"聚宽.{function_name}() 返回空数据")
    
    # PIT 处理
    pit_config = factor.get("pit_requirement", {})
    if pit_config.get("need_pit", False):
        df = _add_observation_date(df, pit_config)
    
    return df


def _get_futures_daily(params: Dict[str, Any]) -> pd.DataFrame:
    """获取期货日线数据
    
    Args:
        params: 包含 code, start_date, end_date 等参数
        
    Returns:
        日线数据 DataFrame
    """
    from jqdatasdk import get_price
    
    code = params.get("code")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    frequency = params.get("frequency", "daily")
    
    if not code:
        raise ValueError("需要 code 参数")
    
    # 聚宽期货代码格式：品种代码 + 交易所（如 ru2405.XSHG）
    df = get_price(code, start_date=start_date, end_date=end_date, 
                   frequency=frequency, fields=['open', 'high', 'low', 'close', 'volume', 'open_interest'])
    
    return df


def _get_futures_contracts(params: Dict[str, Any]) -> pd.DataFrame:
    """获取期货合约列表
    
    Args:
        params: 包含 exchange, date 等参数
        
    Returns:
        合约列表 DataFrame
    """
    from jqdatasdk import get_futures_contracts
    
    exchange = params.get("exchange", "CCFX")  # CCFX=中金所，SHFE=上期所，DCE=大商所，CZCE=郑商所
    date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    df = get_futures_contracts(exchange, date)
    
    return df


def _get_macro_data(params: Dict[str, Any]) -> pd.DataFrame:
    """获取宏观数据
    
    Args:
        params: 包含 indicator, start_date, end_date 等参数
        
    Returns:
        宏观数据 DataFrame
    """
    from jqdatasdk import macro
    
    indicator = params.get("indicator")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    
    if not indicator:
        raise ValueError("需要 indicator 参数")
    
    # 聚宽宏观数据接口
    df = macro(indicator, start_date=start_date, end_date=end_date)
    
    return df


def _get_price(params: Dict[str, Any]) -> pd.DataFrame:
    """获取价格数据（通用接口）
    
    Args:
        params: 包含 code, start_date, end_date, frequency, fields 等参数
        
    Returns:
        价格数据 DataFrame
    """
    from jqdatasdk import get_price
    
    code = params.get("code")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    frequency = params.get("frequency", "daily")
    fields = params.get("fields", ['open', 'high', 'low', 'close', 'volume'])
    
    if not code:
        raise ValueError("需要 code 参数")
    
    df = get_price(code, start_date=start_date, end_date=end_date,
                   frequency=frequency, fields=fields)
    
    return df


def _add_observation_date(df: pd.DataFrame, pit_config: Dict[str, Any]) -> pd.DataFrame:
    """添加观测日期（PIT 数据）
    
    Args:
        df: 原始 DataFrame
        pit_config: PIT 配置
        
    Returns:
        添加 obs_date 列的 DataFrame
    """
    # 简化处理：用当前日期作为观测日期
    df["obs_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return df


# ============ 常用聚宽接口封装 ============

def get_ru_futures_daily(start_date: str, end_date: str) -> pd.DataFrame:
    """获取橡胶期货日线数据
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        
    Returns:
        日线数据 DataFrame
    """
    params = {
        "code": "ru2405.XSHG",
        "start_date": start_date,
        "end_date": end_date
    }
    
    return _get_futures_daily(params)


def get_rb_futures_daily(start_date: str, end_date: str) -> pd.DataFrame:
    """获取螺纹钢期货日线数据
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        
    Returns:
        日线数据 DataFrame
    """
    params = {
        "code": "rb2405.XSHG",
        "start_date": start_date,
        "end_date": end_date
    }
    
    return _get_futures_daily(params)


# ============ 接口函数注册表 ============

FUNCTION_MAP = {
    "get_futures_daily": _get_futures_daily,
    "get_futures_contracts": _get_futures_contracts,
    "get_macro_data": _get_macro_data,
    "get_price": _get_price,
}
