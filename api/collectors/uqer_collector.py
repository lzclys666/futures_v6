"""
优矿 (Uqer) 数据源采集器
========================
封装优矿 API 接口，统一返回 DataFrame

注意：
- 优矿是通联数据旗下的量化平台
- 需要注册账号获取 token
- 支持期货、股票、宏观、基本面等数据

依赖：
    pip install uqer
"""

import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
import os


# 优矿认证信息
UQER_TOKEN = os.getenv("UQER_TOKEN", "")
_uqer_initialized = False


def _ensure_initialized() -> bool:
    """确保优矿 SDK 初始化
    
    Returns:
        是否初始化成功
    """
    global _uqer_initialized
    
    if _uqer_initialized:
        return True
    
    try:
        from uqer import DataApi
        
        if not UQER_TOKEN:
            raise Exception("优矿 token 未配置，请设置环境变量 UQER_TOKEN")
        
        # 初始化 DataApi
        global api
        api = DataApi(token=UQER_TOKEN)
        _uqer_initialized = True
        
        return True
        
    except ImportError:
        raise ImportError("uqer 未安装，请运行：pip install uqer")
    except Exception as e:
        raise Exception(f"优矿认证失败：{str(e)}")


def collect_uqer(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集优矿数据
    
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
    
    # 调用优矿接口
    try:
        if function_name == "futuresBar":
            df = _futures_bar(params)
        elif function_name == "futuresMain":
            df = _futures_main(params)
        elif function_name == "macroData":
            df = _macro_data(params)
        elif function_name == "fundData":
            df = _fund_data(params)
        else:
            raise ValueError(f"不支持的优矿接口：{function_name}")
        
    except Exception as e:
        raise Exception(f"优矿.{function_name}() 调用失败：{str(e)}")
    
    # 数据验证
    if df is None or df.empty:
        raise Exception(f"优矿.{function_name}() 返回空数据")
    
    # PIT 处理
    pit_config = factor.get("pit_requirement", {})
    if pit_config.get("need_pit", False):
        df = _add_observation_date(df, pit_config)
    
    return df


def _futures_bar(params: Dict[str, Any]) -> pd.DataFrame:
    """获取期货分钟/日线数据
    
    Args:
        params: 包含 instrument, beginDate, endDate, frequency 等参数
        
    Returns:
        期货数据 DataFrame
    """
    instrument = params.get("instrument")
    begin_date = params.get("beginDate")
    end_date = params.get("endDate")
    frequency = params.get("frequency", "D")  # D=日线，1m=1 分钟，5m=5 分钟
    
    if not instrument:
        raise ValueError("需要 instrument 参数")
    
    # 优矿期货数据接口
    df = api.futuresBar(
        instrument=instrument,
        beginDate=begin_date,
        endDate=end_date,
        frequency=frequency,
        field=["openPrice", "highPrice", "lowPrice", "closePrice", "volume", "openInt"]
    )
    
    # 重命名列
    df = df.rename(columns={
        "openPrice": "open",
        "highPrice": "high",
        "lowPrice": "low",
        "closePrice": "close",
        "openInt": "open_interest"
    })
    
    return df


def _futures_main(params: Dict[str, Any]) -> pd.DataFrame:
    """获取期货主力合约数据
    
    Args:
        params: 包含 exchange, beginDate, endDate 等参数
        
    Returns:
        主力合约数据 DataFrame
    """
    exchange = params.get("exchange", "SHFE")  # SHFE=上期所，DCE=大商所，CZCE=郑商所，CFFEX=中金所
    begin_date = params.get("beginDate")
    end_date = params.get("endDate")
    
    # 优矿主力合约接口
    df = api.futuresMain(
        exchange=exchange,
        beginDate=begin_date,
        endDate=end_date
    )
    
    return df


def _macro_data(params: Dict[str, Any]) -> pd.DataFrame:
    """获取宏观数据
    
    Args:
        params: 包含 ticker, beginDate, endDate 等参数
        
    Returns:
        宏观数据 DataFrame
    """
    ticker = params.get("ticker")  # 宏观指标代码
    begin_date = params.get("beginDate")
    end_date = params.get("endDate")
    
    if not ticker:
        raise ValueError("需要 ticker 参数")
    
    # 优矿宏观数据接口
    df = api.macroData(
        ticker=ticker,
        beginDate=begin_date,
        endDate=end_date
    )
    
    return df


def _fund_data(params: Dict[str, Any]) -> pd.DataFrame:
    """获取基金数据
    
    Args:
        params: 包含 secID, beginDate, endDate 等参数
        
    Returns:
        基金数据 DataFrame
    """
    sec_id = params.get("secID")
    begin_date = params.get("beginDate")
    end_date = params.get("endDate")
    
    # 优矿基金数据接口
    df = api.fundData(
        secID=sec_id,
        beginDate=begin_date,
        endDate=end_date
    )
    
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


# ============ 常用优矿接口封装 ============

def get_ru_futures_bar(instrument: str, begin_date: str, end_date: str) -> pd.DataFrame:
    """获取橡胶期货数据
    
    Args:
        instrument: 合约代码（如 RU2405.SHF）
        begin_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        
    Returns:
        期货数据 DataFrame
    """
    params = {
        "instrument": instrument,
        "beginDate": begin_date,
        "endDate": end_date,
        "frequency": "D"
    }
    
    return _futures_bar(params)


def get_macro_cpi(begin_date: str, end_date: str) -> pd.DataFrame:
    """获取 CPI 宏观数据
    
    Args:
        begin_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        
    Returns:
        CPI 数据 DataFrame
    """
    params = {
        "ticker": "M0000523",  # CPI:当月同比
        "beginDate": begin_date,
        "endDate": end_date
    }
    
    return _macro_data(params)


# ============ 接口函数注册表 ============

FUNCTION_MAP = {
    "futuresBar": _futures_bar,
    "futuresMain": _futures_main,
    "macroData": _macro_data,
    "fundData": _fund_data,
}
