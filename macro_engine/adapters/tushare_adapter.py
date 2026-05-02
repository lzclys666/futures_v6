# adapters/tushare_adapter.py
# Tushare适配器实现

import pandas as pd
from typing import Optional
import logging

from .base import DataSourceAdapter, AdapterResult

logger = logging.getLogger(__name__)


class TushareAdapter(DataSourceAdapter):
    """
    Tushare Pro数据源适配器
    
    作为AKShare的备用数据源
    需要配置TUSHARE_TOKEN环境变量
    
    支持的数据:
    - 期货现货价格 (需要pro期货数据权限)
    - 期货库存 (需要现货数据权限)
    - 宏观数据
    """
    
    name = "tushare"
    priority = 2  # 备用优先级
    is_available = False
    _token_set = False
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化Tushare适配器
        
        Parameters:
        -----------
        token: Tushare Pro token，如果为None则从环境变量TUSHARE_TOKEN读取
        """
        self._token = token
        self._pro = None
        self._init_tushare()
    
    def _init_tushare(self) -> None:
        """初始化Tushare连接"""
        try:
            import os
            token = self._token or os.environ.get("TUSHARE_TOKEN")
            if token:
                import tushare as ts
                ts.set_token(token)
                self._pro = ts.pro_api()
                self._token_set = True
                logger.info("Tushare适配器初始化成功")
            else:
                logger.warning("未配置TUSHARE_TOKEN环境变量")
                self._token_set = False
        except ImportError:
            logger.warning("Tushare未安装: pip install tushare")
            self._token_set = False
        except Exception as e:
            logger.warning(f"Tushare初始化失败: {e}")
            self._token_set = False
    
    def check_health(self) -> bool:
        """检查Tushare是否可用"""
        if not self._token_set or self._pro is None:
            self.is_available = False
            return False
        try:
            # 简单测试API
            self._pro.trade_cal(exchange="SSE", start_date="20260401", end_date="20260401")
            self.is_available = True
            return True
        except Exception as e:
            logger.warning(f"Tushare健康检查失败: {e}")
            self.is_available = False
            return False
    
    def _convert_date(self, date_str: Optional[str]) -> Optional[str]:
        """转换日期格式"""
        if date_str is None:
            return None
        # 假设输入格式为 YYYYMMDD，转换为 YYYY-MM-DD
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str
    
    def futures_spot_price(self, symbol: str, date: str) -> AdapterResult:
        """
        获取期货现货价格
        
        Tushare现货数据接口
        """
        if not self.check_health():
            return AdapterResult(
                data=None,
                error="Tushare未配置或不可用",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        
        try:
            # Tushare期货现货数据需要特定权限
            # 这里使用商品现货数据接口作为替代
            # 期货现货数据 pro.daily 基本金属序列
            date_fmt = self._convert_date(date)
            
            # 期货主连品种映射
            symbol_map = {
                "AU": "AU",
                "AG": "AG", 
                "CU": "CU",
                "AL": "AL",
                "ZN": "ZN",
                "PB": "PB",
                "NI": "NI",
                "SN": "SN",
                "RU": "RU",
                "RB": "RB",
                "HC": "HC",
            }
            
            ts_code = symbol_map.get(symbol)
            if not ts_code:
                return AdapterResult(
                    data=None,
                    error=f"不支持的品种: {symbol}",
                    source_name=self.name,
                    confidence=0.9,
                    is_success=False
                )
            
            # 尝试获取期货数据
            df = self._pro.fut_daily(ts_code=ts_code, start_date=date_fmt, end_date=date_fmt)
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=0.9,
                    is_success=True
                )
            
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"Tushare futures_spot_price 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def futures_inventory(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """
        获取期货库存数据
        
        Tushare没有直接的期货库存接口，使用仓单数据作为替代
        """
        if not self.check_health():
            return AdapterResult(
                data=None,
                error="Tushare未配置或不可用",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        
        try:
            # Tushare期货仓单数据
            date_fmt = self._convert_date(date) if date else None
            
            # 使用SHFE仓单数据作为库存参考
            df = self._pro.fut_shfe_daily(start_date=date_fmt, end_date=date_fmt)
            
            if df is not None and not df.empty:
                # 筛选指定品种
                if symbol in df['variety'].values:
                    df = df[df['variety'] == symbol]
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=0.9,
                    is_success=True
                )
            
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"Tushare futures_inventory 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def futures_open_interest(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取期货持仓量"""
        if not self.check_health():
            return AdapterResult(
                data=None,
                error="Tushare未配置或不可用",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        
        try:
            date_fmt = self._convert_date(date) if date else None
            df = self._pro.fut_daily(ts_code=symbol, start_date=date_fmt, end_date=date_fmt)
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=0.9,
                    is_success=True
                )
            
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"Tushare futures_open_interest 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def exchange_rank(self, exchange: str, date: Optional[str] = None) -> AdapterResult:
        """获取交易所持仓排名 (Tushare不支持，需要使用AKShare)"""
        return AdapterResult(
            data=None,
            error="Tushare不支持交易所持仓排名，请使用AKShare",
            source_name=self.name,
            confidence=0.9,
            is_success=False
        )
    
    def bond_yield(self, bond_type: str = "US10Y") -> AdapterResult:
        """获取国债收益率"""
        if not self.check_health():
            return AdapterResult(
                data=None,
                error="Tushare未配置或不可用",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        
        try:
            # Tushare债券数据
            df = self._pro.cn_bond_treasury_yield(start_date="20260401", end_date="20260430")
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=0.9,
                    is_success=True
                )
            
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"Tushare bond_yield 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def precious_metal_spot(self, metal: str = "AU") -> AdapterResult:
        """获取贵金属现货价格"""
        if not self.check_health():
            return AdapterResult(
                data=None,
                error="Tushare未配置或不可用",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        
        try:
            # Tushare贵金属现货数据
            if metal == "AU":
                df = self._pro.cn_gold(start_date="20260401", end_date="20260430")
            else:
                df = None
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=0.9,
                    is_success=True
                )
            
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"Tushare precious_metal_spot 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def macro_data(self, indicator: str, country: str = "US") -> AdapterResult:
        """获取宏观数据"""
        if not self.check_health():
            return AdapterResult(
                data=None,
                error="Tushare未配置或不可用",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        
        try:
            # Tushare宏观数据
            if country == "CN":
                df = self._pro.cn_gdp()
            else:
                # Tushare国际宏观数据
                df = self._pro.us_treasury_yield(start_date="20260401", end_date="20260430")
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=0.9,
                    is_success=True
                )
            
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"Tushare macro_data 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def lme_stock(self, metal: str) -> AdapterResult:
        """获取LME库存 (Tushare不支持)"""
        return AdapterResult(
            data=None,
            error="Tushare不支持LME库存数据",
            source_name=self.name,
            confidence=0.9,
            is_success=False
        )
    
    def warehouse_receipt(self, exchange: str, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取仓单数据"""
        if not self.check_health():
            return AdapterResult(
                data=None,
                error="Tushare未配置或不可用",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        
        try:
            date_fmt = self._convert_date(date) if date else None
            
            if exchange.upper() == "SHFE":
                df = self._pro.fut_shfe_daily(start_date=date_fmt, end_date=date_fmt)
            elif exchange.upper() == "DCE":
                df = self._pro.fut_dce_daily(start_date=date_fmt, end_date=date_fmt)
            else:
                df = self._pro.fut_shfe_daily(start_date=date_fmt, end_date=date_fmt)
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=0.9,
                    is_success=True
                )
            
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"Tushare warehouse_receipt 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )


# 单例实例
_tushare_adapter = None


def get_tushare_adapter() -> TushareAdapter:
    """获取Tushare适配器单例"""
    global _tushare_adapter
    if _tushare_adapter is None:
        _tushare_adapter = TushareAdapter()
    return _tushare_adapter
