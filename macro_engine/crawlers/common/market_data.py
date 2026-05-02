# -*- coding: utf-8 -*-
"""
crawlers/common/market_data.py
公共行情数据接口 - 封装高频 AKShare 调用

目的：减少爬虫脚本中的重复代码，统一错误处理，统一字段名映射。

使用方式:
    from common.market_data import (
        get_main_futures_price,
        get_spot_price,
        get_inventory,
        get_rank_net_position,
    )

每个函数保证返回统一格式：(value, error_msg) 或 (None, error_msg)
调用方只需做最后的合理性校验和写入。
"""
import akshare as ak
import datetime

# ============================================================
# 通用工具
# ============================================================

def _call(func, *args, **kwargs):
    """统一调用包装器：捕获异常"""
    try:
        result = func(*args, **kwargs)
        return result, None
    except TypeError as e:
        if "NoneType" in str(e) or "not iterable" in str(e):
            return None, f"AKShare返回None或空: {e}"
        return None, f"TypeError: {e}"
    except Exception as e:
        return None, f"{func.__name__}: {e}"


def _extract_value(df, price_col=None, row_idx=-1):
    """从 DataFrame 提取数值（默认取最后一行）"""
    if df is None:
        return None, "DataFrame为None"
    if not hasattr(df, "iloc"):
        return None, f"不是DataFrame: {type(df)}"
    if len(df) == 0:
        return None, "DataFrame为空"
    try:
        if price_col:
            col = _find_col(df, price_col)
        else:
            col = df.columns[0]
        val = float(df.iloc[row_idx][col])
        return val, None
    except (ValueError, TypeError, KeyError, IndexError) as e:
        return None, f"提取数值失败: {e}"


def _find_col(df, name):
    """模糊匹配列名（支持中文/英文关键字）"""
    name_lower = name.lower()
    for col in df.columns:
        if name_lower in str(col).lower():
            return col
    return df.columns[0]


# ============================================================
# 主力期货行情（持仓量、收盘价）
# futures_main_sina(symbol)  → 历史K线（需加"0"后缀取主力）
# ============================================================

def get_main_futures_price(symbol, field="收盘"):
    """
    获取主力期货合约价格（取最新一根K线）。

    参数:
        symbol: 品种代码，如 "AG", "AL", "RB"（自动追加"0"后缀取主力）
        field:  字段名关键字（中文），如 "收盘", "结算"
    返回:
        (float, None) 或 (None, error_msg)
    """
    code = symbol if symbol.endswith("0") else symbol + "0"
    df, err = _call(ak.futures_main_sina, symbol=code)
    if err:
        return None, err
    return _extract_value(df, price_col=field)


def get_main_futures_holding(symbol):
    """获取主力期货持仓量（手）"""
    code = symbol if symbol.endswith("0") else symbol + "0"
    df, err = _call(ak.futures_main_sina, symbol=code)
    if err:
        return None, err
    return _extract_value(df, price_col="持仓")


def get_main_futures_oi(symbol):
    """获取主力合约持仓量（OI），主力期货+日线双接口兜底"""
    code = symbol if symbol.endswith("0") else symbol + "0"
    df, err = _call(ak.futures_main_sina, symbol=code)
    if err:
        df, err2 = _call(ak.futures_zh_daily_sina, symbol=code)
        if err2:
            return None, f"{err} | 降级失败: {err2}"
    return _extract_value(df, price_col="持仓量")


# ============================================================
# 现货价格
# futures_spot_price(date="YYYYMMDD", vars_list=["品种"])
# ============================================================

def get_spot_price(symbol, date_str=None):
    """
    获取现货价格。

    参数:
        symbol:    品种代码，如 "螺纹钢", "铜", "铝"
        date_str:  日期字符串，格式 YYYYMMDD，默认取今天
    返回:
        (float, None) 或 (None, error_msg)
    """
    if date_str is None:
        date_str = datetime.date.today().strftime("%Y%m%d")
    df, err = _call(ak.futures_spot_price, date=date_str, vars_list=[symbol])
    if err:
        return None, err
    return _extract_value(df, price_col="spot_price")


# ============================================================
# 期货库存
# futures_inventory_em(symbol="品种")
# ============================================================

def get_inventory(symbol):
    """
    获取品种库存（吨）。多行时 sum 合计。

    返回:
        (float, None) 或 (None, error_msg)
    """
    df, err = _call(ak.futures_inventory_em, symbol=symbol)
    if err:
        return None, err
    if df is None or len(df) == 0:
        return None, "库存DataFrame为空"
    try:
        col = _find_col(df, "库存") or _find_col(df, "仓单")
        if col is None:
            return None, f"库存列未找到，列名: {list(df.columns)}"
        total = float(df[col].sum())
        return total, None
    except Exception as e:
        return None, f"库存提取失败: {e}"


# ============================================================
# 持仓排名
# get_shfe_rank_table(date="YYYYMMDD", vars_list=["品种"]) → dict
# ============================================================

def get_rank_net_position(symbol):
    """
    获取 SHFE 品种净持仓（多头-空头，手）。
    仅适用于上期所品种（AL/CU/ZN/PB/NI/SS/RU/BR/AG/AU）。

    返回:
        (float, None) 或 (None, error_msg)
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    data, err = _call(ak.get_shfe_rank_table, date=today_str, vars_list=[symbol.upper()])
    if err:
        return None, err
    if not isinstance(data, dict):
        return None, f"返回类型错误: {type(data)}，期望dict"
    df = data.get(symbol.upper())
    if df is None or len(df) == 0:
        return None, f"排名表为空（{symbol}）"
    try:
        long_col = _find_col(df, "多头持仓")
        short_col = _find_col(df, "空头持仓")
        if long_col and short_col:
            long_total = float(df[long_col].sum())
            short_total = float(df[short_col].sum())
            return long_total - short_total, None
        net_col = _find_col(df, "净持仓")
        if net_col:
            return float(df[net_col].sum()), None
        return None, f"无法识别持仓排名列，列名: {list(df.columns)}"
    except Exception as e:
        return None, f"持仓排名提取失败: {e}"


def get_rank_concentration(symbol):
    """
    获取前5名会员多头+空头持仓合计（手）。

    返回:
        (float, None) 或 (None, error_msg)
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    data, err = _call(ak.get_shfe_rank_table, date=today_str, vars_list=[symbol.upper()])
    if err:
        return None, err
    if not isinstance(data, dict):
        return None, f"返回类型错误: {type(data)}"
    df = data.get(symbol.upper())
    if df is None or len(df) == 0:
        return None, f"排名表为空（{symbol}）"
    try:
        long_col = _find_col(df, "多头持仓")
        short_col = _find_col(df, "空头持仓")
        if long_col and short_col:
            return (float(df[long_col].sum()) + float(df[short_col].sum())) / 2, None
        return None, "缺少多头/空头列"
    except Exception as e:
        return None, f"集中度提取失败: {e}"


# ============================================================
# 日度行情
# futures_zh_daily_sina(symbol)
# ============================================================

def get_daily_price(symbol, date_str=None):
    """
    获取日度行情收盘价。默认取最新一根K线。

    返回:
        (float, None) 或 (None, error_msg)
    """
    df, err = _call(ak.futures_zh_daily_sina, symbol=symbol)
    if err:
        return None, err
    if df is None or len(df) == 0:
        return None, "日线DataFrame为空"
    try:
        close_col = _find_col(df, "收盘")
        return float(df.iloc[-1][close_col]), None
    except Exception as e:
        return None, f"日线提取失败: {e}"
