# adapters/__init__.py
# 期货数据采集适配器层
# 提供统一的数据源接口，支持多源自动切换

from .base import DataSourceAdapter, AdapterRegistry, AdapterResult
from .akshare_adapter import AKShareAdapter
from .tushare_adapter import TushareAdapter
from .exchange_adapter import ExchangeAdapter
from .adapter_manager import AdapterManager, get_adapter_manager, FailoverMode

__all__ = [
    "DataSourceAdapter",
    "AdapterRegistry",
    "AdapterResult",
    "AKShareAdapter",
    "TushareAdapter", 
    "ExchangeAdapter",
    "AdapterManager",
    "get_adapter_manager",
    "FailoverMode",
]
