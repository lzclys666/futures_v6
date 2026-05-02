# adapters/adapter_manager.py
# 适配器管理器 - 负责多适配器协调和自动切换

import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from .base import DataSourceAdapter, AdapterResult, AdapterRegistry

logger = logging.getLogger(__name__)


class FailoverMode(Enum):
    """故障切换模式"""
    FAILOVER = "failover"  # 主失败后自动切换到备用
    FALLBACK = "fallback"  # 尝试所有适配器，返回最佳结果
    PRIMARY_ONLY = "primary_only"  # 只使用主适配器


@dataclass
class DataRequest:
    """数据请求配置"""
    data_type: str  # 数据类型: spot_price, inventory, open_interest, etc.
    symbol: str  # 品种代码
    date: Optional[str] = None  # 日期
    params: Optional[Dict[str, Any]] = None  # 其他参数
    failover_mode: FailoverMode = FailoverMode.FAILOVER
    

class AdapterManager:
    """
    适配器管理器
    
    核心功能:
    1. 管理多个数据源适配器
    2. 实现自动故障切换 (failover)
    3. 支持按数据类型选择适配器
    4. 记录调用日志和失败统计
    """
    
    def __init__(self):
        self.registry = AdapterRegistry()
        self._method_map: Dict[str, str] = {
            # data_type -> adapter method name
            "spot_price": "futures_spot_price",
            "spot": "futures_spot_price",
            "inventory": "futures_inventory",
            "inv": "futures_inventory",
            "open_interest": "futures_open_interest",
            "oi": "futures_open_interest",
            "rank": "exchange_rank",
            "exchange_rank": "exchange_rank",
            "bond_yield": "bond_yield",
            "bond": "bond_yield",
            "precious_metal": "precious_metal_spot",
            "pm": "precious_metal_spot",
            "macro": "macro_data",
            "lme": "lme_stock",
            "warehouse_receipt": "warehouse_receipt",
            "wr": "warehouse_receipt",
        }
        self._failover_stats: Dict[str, Dict[str, int]] = {}  # 故障统计
    
    def register_adapter(self, adapter: DataSourceAdapter) -> None:
        """注册适配器"""
        self.registry.register(adapter)
        logger.info(f"注册适配器: {adapter.name} (优先级: {adapter.priority})")
    
    def get_data(
        self,
        data_type: str,
        symbol: str,
        date: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        failover_mode: FailoverMode = FailoverMode.FAILOVER,
    ) -> AdapterResult:
        """
        获取数据的统一入口
        
        Parameters:
        -----------
        data_type: 数据类型 (spot_price, inventory, etc.)
        symbol: 品种代码
        date: 日期
        params: 额外参数
        failover_mode: 故障切换模式
        
        Returns:
        --------
        AdapterResult: 第一个成功的结果，或所有失败后的最终结果
        """
        # 获取适配器方法
        method_name = self._method_map.get(data_type.lower())
        if not method_name:
            return AdapterResult(
                data=None,
                error=f"未知数据类型: {data_type}",
                source_name="",
                confidence=0.0,
                is_success=False
            )
        
        # 获取可用适配器列表
        adapters = self.registry.get_available()
        if not adapters:
            return AdapterResult(
                data=None,
                error="无可用数据源适配器",
                source_name="",
                confidence=0.0,
                is_success=False
            )
        
        # 尝试每个适配器
        last_result = None
        for adapter in adapters:
            result = self._call_adapter_method(adapter, method_name, symbol, date, params)
            last_result = result
            
            if result.succeeded:
                logger.info(f"[{adapter.name}] {data_type}/{symbol} 成功 (confidence: {result.confidence})")
                return result
            
            logger.warning(f"[{adapter.name}] {data_type}/{symbol} 失败: {result.error}")
            self._record_failure(adapter.name, data_type)
        
        # 所有适配器都失败
        if last_result:
            logger.error(f"所有适配器失败，最后错误: {last_result.error}")
        else:
            last_result = AdapterResult(
                data=None,
                error="所有适配器均失败",
                source_name="",
                confidence=0.0,
                is_success=False
            )
        
        return last_result
    
    def _call_adapter_method(
        self,
        adapter: DataSourceAdapter,
        method_name: str,
        symbol: str,
        date: Optional[str],
        params: Optional[Dict[str, Any]],
    ) -> AdapterResult:
        """调用适配器方法"""
        try:
            method = getattr(adapter, method_name)
            
            # 根据方法签名调用
            if method_name == "futures_spot_price":
                return method(symbol, date or "")
            elif method_name == "futures_inventory":
                return method(symbol, date)
            elif method_name == "futures_open_interest":
                return method(symbol, date)
            elif method_name == "exchange_rank":
                return method(symbol, date)
            elif method_name == "bond_yield":
                bond_type = (params or {}).get("bond_type", "US10Y")
                return method(bond_type)
            elif method_name == "precious_metal_spot":
                metal = (params or {}).get("metal", "AU")
                return method(metal)
            elif method_name == "macro_data":
                indicator = (params or {}).get("indicator", "CPI")
                country = (params or {}).get("country", "US")
                return method(indicator, country)
            elif method_name == "lme_stock":
                return method(symbol)
            elif method_name == "warehouse_receipt":
                exchange = (params or {}).get("exchange", "SHFE")
                return method(exchange, symbol, date)
            else:
                return method(symbol, date)
        except AttributeError as e:
            logger.error(f"适配器 {adapter.name} 没有方法 {method_name}: {e}")
            return AdapterResult(
                data=None,
                error=f"方法不存在: {method_name}",
                source_name=adapter.name,
                confidence=0.0,
                is_success=False
            )
        except Exception as e:
            logger.error(f"适配器 {adapter.name} 调用失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=adapter.name,
                confidence=0.0,
                is_success=False
            )
    
    def _record_failure(self, adapter_name: str, data_type: str) -> None:
        """记录失败统计"""
        if adapter_name not in self._failover_stats:
            self._failover_stats[adapter_name] = {}
        self._failover_stats[adapter_name][data_type] = \
            self._failover_stats[adapter_name].get(data_type, 0) + 1
    
    def get_failover_stats(self) -> Dict[str, Dict[str, int]]:
        """获取故障统计"""
        return self._failover_stats.copy()
    
    def reset_stats(self) -> None:
        """重置故障统计"""
        self._failover_stats.clear()
    
    def list_adapters(self) -> List[Dict[str, Any]]:
        """列出所有适配器"""
        return self.registry.list_all()
    
    def check_all_health(self) -> Dict[str, bool]:
        """检查所有适配器健康状态"""
        results = {}
        for adapter in self.registry._adapters:
            results[adapter.name] = adapter.check_health()
        return results
    
    # 便捷方法
    
    def get_spot_price(self, symbol: str, date: str) -> AdapterResult:
        """获取现货价格"""
        return self.get_data("spot_price", symbol, date)
    
    def get_inventory(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取库存数据"""
        return self.get_data("inventory", symbol, date)
    
    def get_open_interest(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取持仓量"""
        return self.get_data("open_interest", symbol, date)
    
    def get_exchange_rank(self, exchange: str, date: Optional[str] = None) -> AdapterResult:
        """获取交易所排名"""
        return self.get_data("rank", exchange, date)
    
    def get_bond_yield(self, bond_type: str = "US10Y") -> AdapterResult:
        """获取国债收益率"""
        return self.get_data("bond_yield", "", params={"bond_type": bond_type})
    
    def get_precious_metal(self, metal: str = "AU") -> AdapterResult:
        """获取贵金属现货"""
        return self.get_data("precious_metal", "", params={"metal": metal})
    
    def get_macro_data(self, indicator: str, country: str = "US") -> AdapterResult:
        """获取宏观数据"""
        return self.get_data("macro", "", params={"indicator": indicator, "country": country})
    
    def get_lme_stock(self, metal: str) -> AdapterResult:
        """获取LME库存"""
        return self.get_data("lme", metal)
    
    def get_warehouse_receipt(self, exchange: str, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取仓单数据"""
        return self.get_data("warehouse_receipt", symbol, date, {"exchange": exchange})


# 全局适配器管理器实例
_manager: Optional[AdapterManager] = None


def get_adapter_manager() -> AdapterManager:
    """获取全局适配器管理器单例"""
    global _manager
    if _manager is None:
        _manager = _create_default_manager()
    return _manager


def _create_default_manager() -> AdapterManager:
    """创建默认配置的适配器管理器"""
    from .akshare_adapter import AKShareAdapter
    from .tushare_adapter import TushareAdapter
    from .exchange_adapter import ExchangeAdapter
    
    manager = AdapterManager()
    
    # 注册适配器 (按优先级)
    manager.register_adapter(AKShareAdapter())
    manager.register_adapter(TushareAdapter())
    manager.register_adapter(ExchangeAdapter())
    
    return manager


def init_adapter_manager(
    akshare_enabled: bool = True,
    tushare_token: Optional[str] = None,
    exchange_enabled: bool = True,
) -> AdapterManager:
    """
    初始化适配器管理器
    
    Parameters:
    -----------
    akshare_enabled: 是否启用AKShare
    tushare_token: Tushare token (可选)
    exchange_enabled: 是否启用交易所直连
    
    Returns:
    --------
    AdapterManager
    """
    from .akshare_adapter import AKShareAdapter
    from .tushare_adapter import TushareAdapter
    from .exchange_adapter import ExchangeAdapter
    
    manager = AdapterManager()
    
    if akshare_enabled:
        manager.register_adapter(AKShareAdapter())
    
    if tushare_token:
        manager.register_adapter(TushareAdapter(token=tushare_token))
    
    if exchange_enabled:
        manager.register_adapter(ExchangeAdapter())
    
    global _manager
    _manager = manager
    return manager
