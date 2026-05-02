"""
Wind 数据源采集器
=================
封装 Wind PyAPI 接口，统一返回 DataFrame

注意：
- Wind 是商业数据源，需要机构账号授权
- 需要在安装了 Wind 终端的机器上运行
- 部分接口有访问频率限制

依赖：
    pip install WindPy
"""

import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import os


# Wind 连接状态
_wind_connected = False
_wind_conn = None


def _ensure_connection() -> bool:
    """确保 Wind 连接
    
    Returns:
        是否连接成功
    """
    global _wind_connected, _wind_conn
    
    if _wind_connected and _wind_conn is not None:
        return True
    
    try:
        from WindPy import w
        
        # 初始化连接
        result = w.start()
        
        if result.ErrorCode != 0:
            raise Exception(f"Wind 连接失败：{result.ErrorMessage}")
        
        _wind_connected = True
        _wind_conn = w
        
        return True
        
    except ImportError:
        raise ImportError("WindPy 未安装，请运行：pip install WindPy")
    except Exception as e:
        raise Exception(f"Wind 连接失败：{str(e)}")


def collect_wind(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集 Wind 数据
    
    Args:
        factor: 因子配置，包含 api_params 等
        
    Returns:
        采集到的数据 DataFrame
        
    Raises:
        Exception: 采集失败时抛出异常
    """
    # 确保连接
    _ensure_connection()
    
    api_params = factor.get("api_params", {})
    function_name = api_params.get("function")
    
    if not function_name:
        raise ValueError("api_params.function 未指定")
    
    # 准备参数
    params = {k: v for k, v in api_params.items() if k != "function"}
    
    # 调用 Wind 接口
    try:
        if function_name == "wss":
            # 截面数据
            df = _call_wss(params)
        elif function_name == "wsd":
            # 时间序列数据
            df = _call_wsd(params)
        elif function_name == "wset":
            # 板块数据
            df = _call_wset(params)
        elif function_name == "edb":
            # 宏观数据
            df = _call_edb(params)
        else:
            raise ValueError(f"不支持的 Wind 接口：{function_name}")
        
    except Exception as e:
        raise Exception(f"Wind.{function_name}() 调用失败：{str(e)}")
    
    # 数据验证
    if df is None or df.empty:
        raise Exception(f"Wind.{function_name}() 返回空数据")
    
    # PIT 处理
    pit_config = factor.get("pit_requirement", {})
    if pit_config.get("need_pit", False):
        df = _add_observation_date(df, pit_config, function_name)
    
    return df


def _call_wss(params: Dict[str, Any]) -> pd.DataFrame:
    """调用 Wind 截面数据接口 (wss)
    
    Args:
        params: 包含 codes, fields, options 等参数
        
    Returns:
        数据 DataFrame
    """
    from WindPy import w
    
    codes = params.get("codes", [])
    fields = params.get("fields", [])
    options = params.get("options", {})
    
    if not codes or not fields:
        raise ValueError("wss 需要 codes 和 fields 参数")
    
    # 转换 options 为 Wind 格式
    options_str = ",".join([f"{k}={v}" for k, v in options.items()])
    
    result = w.wss(",".join(codes), ",".join(fields), options_str)
    
    if result.ErrorCode != 0:
        raise Exception(f"Wind wss 错误：{result.ErrorMessage}")
    
    # 转换为 DataFrame
    df = pd.DataFrame(result.Data, index=result.Fields, columns=result.Codes).T
    
    return df


def _call_wsd(params: Dict[str, Any]) -> pd.DataFrame:
    """调用 Wind 时间序列接口 (wsd)
    
    Args:
        params: 包含 codes, fields, start_date, end_date, options 等参数
        
    Returns:
        数据 DataFrame
    """
    from WindPy import w
    
    codes = params.get("codes", [])
    fields = params.get("fields", [])
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    options = params.get("options", {})
    
    if not codes or not fields:
        raise ValueError("wsd 需要 codes 和 fields 参数")
    
    # 转换 options 为 Wind 格式
    options_str = ",".join([f"{k}={v}" for k, v in options.items()])
    
    result = w.wsd(",".join(codes), ",".join(fields), start_date, end_date, options_str)
    
    if result.ErrorCode != 0:
        raise Exception(f"Wind wsd 错误：{result.ErrorMessage}")
    
    # 转换为 DataFrame
    df = pd.DataFrame(result.Data, index=result.Times, columns=result.Fields)
    df.index = pd.to_datetime(df.index)
    
    return df


def _call_wset(params: Dict[str, Any]) -> pd.DataFrame:
    """调用 Wind 板块数据接口 (wset)
    
    Args:
        params: 包含 table_name, fields, options 等参数
        
    Returns:
        数据 DataFrame
    """
    from WindPy import w
    
    table_name = params.get("table_name")
    fields = params.get("fields", [])
    options = params.get("options", {})
    
    if not table_name:
        raise ValueError("wset 需要 table_name 参数")
    
    # 转换 options 为 Wind 格式
    options_str = ",".join([f"{k}={v}" for k, v in options.items()])
    
    result = w.wset(table_name, f"fields={','.join(fields)};{options_str}")
    
    if result.ErrorCode != 0:
        raise Exception(f"Wind wset 错误：{result.ErrorMessage}")
    
    # 转换为 DataFrame
    df = pd.DataFrame(result.Data, columns=result.Fields)
    
    return df


def _call_edb(params: Dict[str, Any]) -> pd.DataFrame:
    """调用 Wind 宏观数据接口 (edb)
    
    Args:
        params: 包含 indicators, start_date, end_date 等参数
        
    Returns:
        数据 DataFrame
    """
    from WindPy import w
    
    indicators = params.get("indicators", [])
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    options = params.get("options", {})
    
    if not indicators:
        raise ValueError("edb 需要 indicators 参数")
    
    # 转换 options 为 Wind 格式
    options_str = ",".join([f"{k}={v}" for k, v in options.items()])
    
    result = w.edb(",".join(indicators), start_date, end_date, options_str)
    
    if result.ErrorCode != 0:
        raise Exception(f"Wind edb 错误：{result.ErrorMessage}")
    
    # 转换为 DataFrame
    df = pd.DataFrame(result.Data, index=result.Times, columns=result.Fields)
    df.index = pd.to_datetime(df.index)
    
    return df


def _add_observation_date(df: pd.DataFrame, pit_config: Dict[str, Any], function_name: str) -> pd.DataFrame:
    """添加观测日期（PIT 数据）
    
    Wind 数据通常有明确的发布日期，但 PyAPI 不直接提供
    实际生产中需要配合数据发布日历
    
    Args:
        df: 原始 DataFrame
        pit_config: PIT 配置
        function_name: 接口名称
        
    Returns:
        添加 obs_date 列的 DataFrame
    """
    # 简化处理：用当前日期作为观测日期
    # 实际生产中应该查询数据发布日历
    df["obs_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return df


# ============ 常用 Wind 接口封装 ============

def get_futures_daily_wind(codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """获取期货日线数据（Wind）
    
    Args:
        codes: 合约代码列表（如 ["RU2405.SHF", "RB2405.SHF"]）
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        
    Returns:
        日线数据 DataFrame
    """
    params = {
        "codes": codes,
        "fields": ["open", "high", "low", "close", "volume", "open_interest"],
        "start_date": start_date,
        "end_date": end_date,
        "options": {"unit": "1"}
    }
    
    return _call_wsd(params)


def get_macro_data_wind(indicators: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """获取宏观数据（Wind）
    
    Args:
        indicators: 指标 ID 列表（如 ["M0000523", "M0000524"]）
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        
    Returns:
        宏观数据 DataFrame
    """
    params = {
        "indicators": indicators,
        "start_date": start_date,
        "end_date": end_date,
        "options": {"fill": "Previous"}
    }
    
    return _call_edb(params)


# ============ 接口函数注册表 ============

FUNCTION_MAP = {
    "wss": _call_wss,
    "wsd": _call_wsd,
    "wset": _call_wset,
    "edb": _call_edb,
}
