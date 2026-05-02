"""
Tushare 数据源采集器
=====================
封装 Tushare 接口，统一返回 DataFrame

注意：
- Tushare 需要 token（环境变量 TUSHARE_TOKEN 或配置文件）
- 部分接口有积分限制
- 宏观数据有发布时滞，需注意 PIT 合规
"""

import pandas as pd
from typing import Dict, Any
from datetime import datetime
import os


# Tushare token 配置
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "your_token_here")


def collect_tushare(factor: Dict[str, Any]) -> pd.DataFrame:
    """采集 Tushare 数据
    
    Args:
        factor: 因子配置，包含 api_params 等
        
    Returns:
        采集到的数据 DataFrame
        
    Raises:
        Exception: 采集失败时抛出异常
    """
    import tushare as ts
    
    api_params = factor.get("api_params", {})
    api_name = api_params.get("api_name")
    
    if not api_name:
        raise ValueError("api_params.api_name 未指定")
    
    # 初始化 pro
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    # 获取 pro 接口函数
    if not hasattr(pro, api_name):
        raise ValueError(f"Tushare 不存在接口: {api_name}")
    
    func = getattr(pro, api_name)
    
    # 准备参数
    params = api_params.get("params", {})
    
    # 调用函数
    try:
        df = func(**params)
    except Exception as e:
        raise Exception(f"Tushare.{api_name}() 调用失败: {str(e)}")
    
    # 数据验证
    if df is None or df.empty:
        raise Exception(f"Tushare.{api_name}() 返回空数据")
    
    # PIT 处理
    pit_config = factor.get("pit_requirement", {})
    if pit_config.get("need_pit", False):
        df = _add_observation_date(df, pit_config, api_name)
    
    return df


def _add_observation_date(df: pd.DataFrame, pit_config: Dict[str, Any], api_name: str) -> pd.DataFrame:
    """添加观测日期（PIT 数据）
    
    宏观数据有发布时滞，需要根据数据发布日期确定 obs_date
    
    Args:
        df: 原始 DataFrame
        pit_config: PIT 配置
        api_name: 接口名称
        
    Returns:
        添加 obs_date 列的 DataFrame
    """
    # 简化处理：用当前日期作为观测日期
    # 实际生产中应该查询数据发布日历
    # 例如 CPI 数据通常在次月 10 号左右发布
    df["obs_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return df


# ============ 常用 Tushare 接口封装 ============

def get_macro_cn_cpi(period_m: str = None) -> pd.DataFrame:
    """获取中国 CPI 数据
    
    Args:
        period_m: 期间（YYYYMM-YYYYMM）
        
    Returns:
        CPI 数据 DataFrame
    """
    import tushare as ts
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    try:
        df = pro.cn_cpi(start_date=period_m[:6] if period_m else None,
                        end_date=period_m[7:] if period_m and len(period_m) > 7 else None)
        return df
    except Exception as e:
        raise Exception(f"获取 CPI 数据失败: {str(e)}")


def get_macro_cn_ppi(period_m: str = None) -> pd.DataFrame:
    """获取中国 PPI 数据
    
    Args:
        period_m: 期间（YYYYMM-YYYYMM）
        
    Returns:
        PPI 数据 DataFrame
    """
    import tushare as ts
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    try:
        df = pro.cn_ppi(start_date=period_m[:6] if period_m else None,
                        end_date=period_m[7:] if period_m and len(period_m) > 7 else None)
        return df
    except Exception as e:
        raise Exception(f"获取 PPI 数据失败: {str(e)}")


def get_macro_cn_pmi(period_m: str = None) -> pd.DataFrame:
    """获取中国 PMI 数据
    
    Args:
        period_m: 期间（YYYYMM-YYYYMM）
        
    Returns:
        PMI 数据 DataFrame
    """
    import tushare as ts
    
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    try:
        df = pro.cn_pmi(start_date=period_m[:6] if period_m else None,
                        end_date=period_m[7:] if period_m and len(period_m) > 7 else None)
        return df
    except Exception as e:
        raise Exception(f"获取 PMI 数据失败: {str(e)}")


# ============ 接口函数注册表 ============

FUNCTION_MAP = {
    "macro_cn_cpi": get_macro_cn_cpi,
    "macro_cn_ppi": get_macro_cn_ppi,
    "macro_cn_pmi": get_macro_cn_pmi,
}
