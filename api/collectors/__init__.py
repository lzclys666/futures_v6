"""
因子数据采集器模块
==================
提供统一的数据采集接口，支持多种数据源

数据源：
- akshare: 免费开源数据源（期货、股票、宏观）
- tushare: 需 token，支持宏观和基本面数据
- custom: 自定义爬虫和 API 请求
- wind: 商业数据源（需 Wind 终端）
- joinquant: 聚宽量化平台（免费）
- uqer: 优矿量化平台（通联数据）
- exchange: 交易所官网爬虫（SHFE/DCE/CZCE/CFFEX/INE）

用法：
    from collectors import collect_akshare, collect_tushare, collect_wind
    from collectors import collect_joinquant, collect_uqer, collect_exchange
    
    # 或者
    from collectors.akshare_collector import collect_akshare
"""

from .akshare_collector import collect_akshare
from .tushare_collector import collect_tushare
from .custom_collector import collect_custom
from .wind_collector import collect_wind
from .joinquant_collector import collect_joinquant
from .uqer_collector import collect_uqer
from .exchange_crawler import collect_exchange

__all__ = [
    "collect_akshare",
    "collect_tushare",
    "collect_custom",
    "collect_wind",
    "collect_joinquant",
    "collect_uqer",
    "collect_exchange",
]
