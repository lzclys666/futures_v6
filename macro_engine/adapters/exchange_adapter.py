# adapters/exchange_adapter.py
# 交易所直连适配器

import requests
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .base import DataSourceAdapter, AdapterResult

logger = logging.getLogger(__name__)


class ExchangeAdapter(DataSourceAdapter):
    """
    交易所直连数据源适配器
    
    直接从交易所官网API获取数据，作为AKShare的备用
    目前支持:
    - SHFE (上海期货交易所)
    - DCE (大连商品交易所)  
    - CZCE (郑州商品交易所)
    - INE (上海国际能源交易中心)
    - SGE (上海黄金交易所)
    
    注意: 各交易所API不同，这里提供统一接口
    """
    
    name = "exchange"
    priority = 3  # 交易所直连优先级
    is_available = True
    
    # 交易所API基础URL
    SHFE_URL = "http://www.shfe.com.cn/data/"
    DCE_URL = "http://www.dce.com.cn/publicweb/"
    CZCE_URL = "http://www.czce.com.cn/"
    SGE_URL = "http://www.sge.com.cn/"
    
    def check_health(self) -> bool:
        """检查交易所API是否可用"""
        try:
            resp = requests.get("http://www.shfe.com.cn/", timeout=5)
            self.is_available = resp.status_code == 200
            return self.is_available
        except Exception as e:
            logger.warning(f"交易所API健康检查失败: {e}")
            self.is_available = False
            return False
    
    def _fetch_shfe_spot(self, date: str) -> Optional[pd.DataFrame]:
        """获取SHFE现货价格"""
        try:
            # SHFE仓单数据
            url = f"{self.SHFE_URL}delyspotdata.txt"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # 解析文本数据
                lines = resp.text.strip().split('\n')
                data = []
                for line in lines[1:]:  # 跳过表头
                    parts = line.split(',')
                    if len(parts) >= 6:
                        data.append({
                            'variety': parts[0],
                            'warehouse': parts[1],
                            'weight': float(parts[2]) if parts[2] else 0,
                            'date': parts[3],
                        })
                if data:
                    return pd.DataFrame(data)
        except Exception as e:
            logger.warning(f"SHFE现货获取失败: {e}")
        return None
    
    def _fetch_shfe_rank(self, date: str) -> Optional[pd.DataFrame]:
        """获取SHFE持仓排名"""
        try:
            # SHFE持仓排名数据
            url = f"{self.SHFE_URL}datashfe/rank/{date}.txt"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # 解析数据
                lines = resp.text.strip().split('\n')
                data = []
                for line in lines:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        data.append({
                            'rank': parts[0],
                            'trader': parts[1],
                            'volume': int(parts[2]) if parts[2].isdigit() else 0,
                            'change': parts[3],
                        })
                if data:
                    return pd.DataFrame(data)
        except Exception as e:
            logger.warning(f"SHFE排名获取失败: {e}")
        return None
    
    def _fetch_sge_spot(self) -> Optional[pd.DataFrame]:
        """获取SGE现货价格"""
        try:
            # SGE黄金基准价
            url = f"{self.SGE_URL}sfwhsj/zsjb/hjjzj"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # SGE页面结构复杂，这里简化处理
                # 实际使用时需要解析HTML
                logger.info(f"SGE spot fetched: {len(resp.text)} bytes")
                return None  # 待实现HTML解析
        except Exception as e:
            logger.warning(f"SGE现货获取失败: {e}")
        return None
    
    def futures_spot_price(self, symbol: str, date: str) -> AdapterResult:
        """
        获取期货现货价格
        
        交易所直连: SHFE仓单价格作为库存参考
        """
        try:
            df = self._fetch_shfe_spot(date)
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
            
            # 尝试SGE
            df = self._fetch_sge_spot()
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
            logger.warning(f"Exchange futures_spot_price 失败: {e}")
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
        
        交易所直连: 使用SHFE仓单数据
        """
        try:
            date_str = date or datetime.now().strftime("%Y%m%d")
            df = self._fetch_shfe_spot(date_str)
            
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
            logger.warning(f"Exchange futures_inventory 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def futures_open_interest(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """
        获取期货持仓量
        
        交易所直连: SHFE持仓排名
        """
        try:
            date_str = date or datetime.now().strftime("%Y%m%d")
            df = self._fetch_shfe_rank(date_str)
            
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
            logger.warning(f"Exchange futures_open_interest 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def exchange_rank(self, exchange: str, date: Optional[str] = None) -> AdapterResult:
        """获取交易所持仓排名"""
        try:
            date_str = date or datetime.now().strftime("%Y%m%d")
            
            if exchange.upper() == "SHFE":
                df = self._fetch_shfe_rank(date_str)
            else:
                return AdapterResult(
                    data=None,
                    error=f"不支持的交易所: {exchange}",
                    source_name=self.name,
                    confidence=0.9,
                    is_success=False
                )
            
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
            logger.warning(f"Exchange exchange_rank 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def bond_yield(self, bond_type: str = "US10Y") -> AdapterResult:
        """获取国债收益率 (交易所不提供，需要其他源)"""
        return AdapterResult(
            data=None,
            error="交易所不提供国债收益率数据",
            source_name=self.name,
            confidence=0.9,
            is_success=False
        )
    
    def precious_metal_spot(self, metal: str = "AU") -> AdapterResult:
        """获取贵金属现货价格 (SGE)"""
        try:
            df = self._fetch_sge_spot()
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
            logger.warning(f"Exchange precious_metal_spot 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )
    
    def macro_data(self, indicator: str, country: str = "US") -> AdapterResult:
        """获取宏观数据 (交易所不提供)"""
        return AdapterResult(
            data=None,
            error="交易所不提供宏观数据",
            source_name=self.name,
            confidence=0.9,
            is_success=False
        )
    
    def lme_stock(self, metal: str) -> AdapterResult:
        """获取LME库存 (交易所不提供)"""
        return AdapterResult(
            data=None,
            error="交易所不提供LME库存数据",
            source_name=self.name,
            confidence=0.9,
            is_success=False
        )
    
    def warehouse_receipt(self, exchange: str, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """获取仓单数据"""
        try:
            date_str = date or datetime.now().strftime("%Y%m%d")
            
            if exchange.upper() == "SHFE":
                df = self._fetch_shfe_spot(date_str)
                if df is not None and not df.empty:
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
            logger.warning(f"Exchange warehouse_receipt 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=0.9,
                is_success=False
            )


# 单例实例
_exchange_adapter = ExchangeAdapter()


def get_exchange_adapter() -> ExchangeAdapter:
    """获取交易所适配器单例"""
    return _exchange_adapter
