# adapters/base.py
# 数据源适配器抽象基类

from abc import ABC, abstractmethod
from typing import Protocol, Optional, List, Dict, Any
from dataclasses import dataclass
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """适配器返回结果"""
    data: Optional[pd.DataFrame]
    error: Optional[str]
    source_name: str
    confidence: float = 1.0
    is_success: bool = False

    @property
    def succeeded(self) -> bool:
        return self.is_success and self.data is not None and not self.data.empty


class DataSourceAdapter(Protocol):
    """
    数据源适配器标准接口
    
    所有数据源适配器必须实现此接口
    支持的数据类型:
    - 期货现货价格 (futures_spot_price)
    - 期货库存/仓单 (futures_inventory)
    - 期货持仓量 (futures_open_interest)
    - 交易所排名 (exchange_rank)
    - 国债收益率 (bond_yield)
    - 宏观数据 (macro_data)
    - 贵金属数据 (precious_metals)
    - LME数据 (lme_data)
    - 仓单数据 (warehouse_receipt)
    """
    
    name: str  # 适配器名称
    priority: int  # 优先级，数字越小优先级越高
    is_available: bool  # 当前是否可用
    
    def futures_spot_price(self, symbol: str, date: str) -> AdapterResult:
        """获取期货现货价格"""
        ...
    
    def futures_inventory(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取期货库存/仓单数据"""
        ...
    
    def futures_open_interest(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取期货持仓量"""
        ...
    
    def exchange_rank(self, exchange: str, date: Optional[str] = None) -> AdapterResult:
        """获取交易所持仓排名"""
        ...
    
    def bond_yield(self, bond_type: str = "US10Y") -> AdapterResult:
        """获取国债收益率"""
        ...
    
    def precious_metal_spot(self, metal: str = "AU") -> AdapterResult:
        """获取贵金属现货价格"""
        ...
    
    def macro_data(self, indicator: str, country: str = "US") -> AdapterResult:
        """获取宏观数据"""
        ...
    
    def lme_stock(self, metal: str) -> AdapterResult:
        """获取LME库存"""
        ...
    
    def warehouse_receipt(self, exchange: str, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取仓单数据"""
        ...
    
    def check_health(self) -> bool:
        """检查适配器是否健康可用"""
        ...


class AdapterRegistry:
    """
    适配器注册表
    管理所有数据源适配器，支持按优先级排序
    """
    
    def __init__(self):
        self._adapters: List[DataSourceAdapter] = []
        self._adapter_map: Dict[str, DataSourceAdapter] = {}
    
    def register(self, adapter: DataSourceAdapter) -> None:
        """注册适配器"""
        self._adapters.append(adapter)
        self._adapter_map[adapter.name] = adapter
        # 按优先级排序
        self._adapters.sort(key=lambda x: x.priority)
        logger.info(f"注册适配器: {adapter.name} (优先级: {adapter.priority})")
    
    def unregister(self, name: str) -> bool:
        """注销适配器"""
        if name in self._adapter_map:
            adapter = self._adapter_map.pop(name)
            self._adapters.remove(adapter)
            logger.info(f"注销适配器: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[DataSourceAdapter]:
        """获取指定名称的适配器"""
        return self._adapter_map.get(name)
    
    def get_available(self) -> List[DataSourceAdapter]:
        """获取所有可用的适配器"""
        return [a for a in self._adapters if a.check_health()]
    
    def get_primary(self) -> Optional[DataSourceAdapter]:
        """获取优先级最高的可用适配器"""
        available = self.get_available()
        return available[0] if available else None
    
    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有适配器状态"""
        return [
            {
                "name": a.name,
                "priority": a.priority,
                "available": a.check_health(),
            }
            for a in self._adapters
        ]
