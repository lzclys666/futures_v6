# adapters/migrate_crawler.py
# 爬虫迁移助手 - 帮助将现有爬虫迁移到适配器层

"""
使用方式:

# 在现有爬虫中替换:
# 
# 旧代码:
#     import akshare as ak
#     df = ak.futures_inventory_em(symbol="橡胶")
#     val = float(df.iloc[-1].iloc[1])
#
# 新代码:
#     from adapters.migrate_crawler import migrate_call
#     result = migrate_call("inventory", symbol="橡胶")
#     if result.succeeded:
#         val = float(result.data.iloc[-1].iloc[1])
#     else:
#         raise ValueError(f"获取失败: {result.error}")

"""

from typing import Optional, Any, Dict
import pandas as pd

from .adapter_manager import get_adapter_manager, FailoverMode
from .base import AdapterResult


def migrate_call(
    data_type: str,
    symbol: Optional[str] = None,
    date: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    failover_mode: FailoverMode = FailoverMode.FAILOVER,
) -> AdapterResult:
    """
    迁移后的统一调用接口
    
    Parameters:
    -----------
    data_type: 数据类型
        - "spot_price": 期货现货价格
        - "inventory": 期货库存
        - "open_interest": 持仓量
        - "rank": 交易所排名
        - "bond_yield": 国债收益率
        - "precious_metal": 贵金属现货
        - "macro": 宏观数据
        - "lme": LME库存
        - "warehouse_receipt": 仓单
    symbol: 品种代码
    date: 日期
    params: 额外参数
    failover_mode: 故障切换模式
    
    Returns:
    --------
    AdapterResult: 包含数据或错误信息
    """
    manager = get_adapter_manager()
    return manager.get_data(
        data_type=data_type,
        symbol=symbol or "",
        date=date,
        params=params,
        failover_mode=failover_mode,
    )


# AKShare函数映射 - 用于快速迁移
AKSHARE_FUNCTION_MAP = {
    # (data_type, symbol_param): (method_name, default_params)
    ("inventory", "橡胶"): ("inventory", {"symbol": "RU"}),
    ("inventory", "沥青"): ("inventory", {"symbol": "沥青"}),
    ("spot_price", None): ("spot_price", {}),
    ("open_interest", None): ("open_interest", {}),
    ("precious_metal", "AU"): ("precious_metal", {"metal": "AU"}),
    ("precious_metal", "AG"): ("precious_metal", {"metal": "AG"}),
    ("bond_yield", "US10Y"): ("bond_yield", {"bond_type": "US10Y"}),
    ("macro", "CPI"): ("macro", {"indicator": "CPI", "country": "US"}),
    ("macro", "NONFARM"): ("macro", {"indicator": "NONFARM", "country": "US"}),
    ("lme", None): ("lme", {}),
}


def migrate_akshare_call(func_name: str, **kwargs) -> AdapterResult:
    """
    迁移AKShare函数调用
    
    自动将akshare函数调用转换为适配器调用
    
    Examples:
    ---------
    # 旧代码:
    #     df = ak.futures_inventory_em(symbol="橡胶")
    #
    # 新代码:
    #     result = migrate_akshare_call("futures_inventory_em", symbol="橡胶")
    #     if result.succeeded:
    #         df = result.data
    """
    # 映射AKShare函数名到data_type
    func_to_datatype = {
        "futures_inventory_em": "inventory",
        "futures_spot_price": "spot_price",
        "futures_main_sina": "open_interest",
        "spot_golden_benchmark_sge": ("precious_metal", {"metal": "AU"}),
        "spot_silver_benchmark_sge": ("precious_metal", {"metal": "AG"}),
        "bond_zh_us_rate": ("bond_yield", {"bond_type": "US10Y"}),
        "macro_usa_cpi_yoy": ("macro", {"indicator": "CPI", "country": "US"}),
        "macro_usa_non_farm": ("macro", {"indicator": "NONFARM", "country": "US"}),
        "macro_usa_dollar_index": ("macro", {"indicator": "DXY", "country": "US"}),
        "macro_euro_lme_stock": ("lme", {}),
        "futures_shfe_warehouse_receipt": ("warehouse_receipt", {"exchange": "SHFE"}),
        "get_shfe_rank_table": ("rank", {"exchange": "SHFE"}),
    }
    
    mapping = func_to_datatype.get(func_name)
    if mapping is None:
        return AdapterResult(
            data=None,
            error=f"未知的AKShare函数: {func_name}",
            source_name="migrate",
            confidence=0.0,
            is_success=False
        )
    
    # 解析映射
    if isinstance(mapping, tuple):
        data_type, default_params = mapping
    else:
        data_type = mapping
        default_params = {}
    
    # 合并参数
    params = {**default_params, **kwargs}
    
    # 提取symbol和date
    symbol = params.pop("symbol", kwargs.get("symbol", ""))
    date = params.pop("date", kwargs.get("date", None))
    
    return migrate_call(data_type, symbol=symbol, date=date, params=params)


class CrawlerMigrator:
    """
    爬虫迁移上下文管理器
    
    使用方式:
    
    with CrawlerMigrator("inventory") as migrator:
        result = migrator.call(symbol="橡胶")
        if result.succeeded:
            df = result.data
    """
    
    def __init__(self, data_type: str):
        self.data_type = data_type
        self.manager = get_adapter_manager()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def call(
        self,
        symbol: Optional[str] = None,
        date: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> AdapterResult:
        """调用适配器"""
        return self.manager.get_data(
            data_type=self.data_type,
            symbol=symbol or "",
            date=date,
            params=params,
        )


# 快速参考: 各数据类型的symbol映射
QUICK_REFERENCE = {
    "inventory": {
        "橡胶": "RU",
        "沥青": "沥青",
        "铜": "铜",
        "铝": "铝",
        "螺纹钢": "螺纹",
        "热卷": "热卷",
        "锌": "锌",
        "镍": "镍",
        "PP": "PP",
        "LLDPE": "PE",
    },
    "spot_price": {
        # symbol -> akshare vars_list
        "AU": "AU", "AG": "AG", "CU": "CU", "AL": "AL",
        "ZN": "ZN", "RU": "RU", "RB": "RB", "HC": "HC",
        "BU": "BU", "JM": "JM", "J": "J",
        "TA": "TA", "MA": "MA", "EG": "EG",
    },
}


def print_migration_guide():
    """打印迁移指南"""
    guide = """
================================================================================
                    爬虫迁移到适配器层指南
================================================================================

1. 导入适配器模块
-----------------
    from adapters.migrate_crawler import migrate_call

2. 替换AKShare调用
-----------------

    # 旧代码:
    import akshare as ak
    df = ak.futures_inventory_em(symbol="橡胶")
    
    # 新代码:
    result = migrate_call("inventory", symbol="橡胶")
    if result.succeeded:
        df = result.data
    else:
        raise ValueError(f"获取失败: {result.error}")

3. 支持的数据类型
-----------------
    - "spot_price":    期货现货价格
    - "inventory":     期货库存
    - "open_interest": 持仓量
    - "rank":          交易所排名
    - "bond_yield":    国债收益率
    - "precious_metal":贵金属现货
    - "macro":         宏观数据
    - "lme":           LME库存
    - "warehouse_receipt": 仓单

4. 故障切换
-----------
    默认启用自动故障切换，主适配器失败后自动尝试备用适配器:
    AKShare → Tushare → Exchange
    
    如需只使用主适配器:
    result = migrate_call(..., failover_mode=FailoverMode.PRIMARY_ONLY)

5. 完整示例
-----------
    from adapters.migrate_crawler import migrate_call, CrawlerMigrator
    
    # 方式1: 函数调用
    result = migrate_call("inventory", symbol="橡胶")
    if result.succeeded:
        val = float(result.data.iloc[-1].iloc[1])
        print(f"[{result.source_name}] 成功: {val}")
    
    # 方式2: 上下文管理器
    with CrawlerMigrator("inventory") as m:
        result = m.call(symbol="橡胶")
        if result.succeeded:
            df = result.data

================================================================================
"""
    print(guide)
