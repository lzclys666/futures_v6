# adapters/akshare_adapter.py
# AKShare适配器实现

import akshare as ak
import pandas as pd
from typing import Optional
from datetime import date, datetime
import logging

from .base import DataSourceAdapter, AdapterResult

logger = logging.getLogger(__name__)


class AKShareAdapter(DataSourceAdapter):
    """
    AKShare数据源适配器
    
    支持的数据:
    - 期货现货价格: ak.futures_spot_price
    - 期货库存: ak.futures_inventory_em
    - 期货持仓量: ak.futures_main_sina
    - 交易所排名: ak.get_shfe_rank_table
    - 国债收益率: ak.bond_zh_us_rate
    - 贵金属现货: ak.spot_golden_benchmark_sge
    - LME库存: ak.macro_euro_lme_stock
    - 仓单数据: ak.futures_shfe_warehouse_receipt
    -宏观数据: ak.macro_usa_cpi_yoy等
    """
    
    name = "akshare"
    priority = 1  # 最高优先级
    is_available = True
    
    # AKShare函数映射表
    SPOT_SYMBOL_MAP = {
        # 期货现货价格 symbol -> akshare vars_list
        "AU": "AU", "AG": "AG", "CU": "CU", "AL": "AL",
        "ZN": "ZN", "PB": "PB", "NI": "NI", "SN": "SN",
        "RU": "RU", "RB": "RB", "HC": "HC", "BU": "BU",
        "JM": "JM", "J": "J", "焦煤": "JM", "焦炭": "J",
        "TA": "TA", "MA": "MA", "EG": "EG", "PP": "PP",
        "L": "L", "V": "V", "PVC": "V",
        "Y": "Y", "P": "P", "M": "M", "RM": "RM",
        "SR": "SR", "CF": "CF", "棉花": "CF", "白糖": "SR",
        "AP": "AP", "苹果": "AP",
    }
    
    INVENTORY_SYMBOL_MAP = {
        # 期货库存 symbol -> akshare symbol
        "RU": "橡胶", "沥青": "沥青", "铜": "铜", "铝": "铝",
        "螺纹": "螺纹钢", "热卷": "热卷", "锌": "锌",
        "镍": "镍", "铅": "铅", "锡": "锡",
        "PP": "PP", "PE": "LLDPE", "LLDPE": "LLDPE",
        "PVC": "PVC", "甲醇": "甲醇", "TA": "PTA",
        "乙二醇": "MEG", "MEG": "MEG",
        "棕榈": "棕榈油", "豆油": "豆油", "菜油": "菜油",
        "豆粕": "豆粕", "菜粕": "菜粕",
    }
    
    def check_health(self) -> bool:
        """检查AKShare是否可用"""
        try:
            # 简单测试: 获取任意数据
            ak.macro_usa_cpi_yoy()
            self.is_available = True
            return True
        except Exception as e:
            logger.warning(f"AKShare健康检查失败: {e}")
            self.is_available = False
            return False
    
    def futures_spot_price(self, symbol: str, date: str) -> AdapterResult:
        """
        获取期货现货价格
        
        Parameters:
        -----------
        symbol: 品种代码 (如 "AU", "AG", "RU")
        date: 日期字符串 (如 "20260422")
        
        Returns:
        --------
        AdapterResult: 包含DataFrame或error
        """
        try:
            # 转换symbol到AKShare格式
            vars_symbol = self.SPOT_SYMBOL_MAP.get(symbol, symbol)
            
            df = ak.futures_spot_price(date=date, vars_list=[vars_symbol])
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except TypeError as e:
            # AKShare接口签名变化处理
            logger.warning(f"AKShare futures_spot_price TypeError (接口变化?): {e}")
            return AdapterResult(
                data=None,
                error=f"TypeError: {e}",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare futures_spot_price 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def futures_inventory(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """
        获取期货库存数据
        
        Parameters:
        -----------
        symbol: 品种代码 (如 "RU", "沥青")
        date: 日期 (可选)
        
        Returns:
        --------
        AdapterResult
        """
        try:
            # 转换symbol到AKShare格式
            ak_symbol = self.INVENTORY_SYMBOL_MAP.get(symbol, symbol)
            
            df = ak.futures_inventory_em(symbol=ak_symbol)
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except TypeError as e:
            logger.warning(f"AKShare futures_inventory TypeError: {e}")
            return AdapterResult(
                data=None,
                error=f"TypeError: {e}",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare futures_inventory 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def futures_open_interest(self, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """
        获取期货持仓量
        
        Parameters:
        -----------
        symbol: 品种代码 (如 "AU0", "JM")
        date: 日期 (可选)
        
        Returns:
        --------
        AdapterResult
        """
        try:
            # 尝试主力合约
            if not symbol.endswith("0"):
                symbol = symbol + "0"
            
            df = ak.futures_main_sina(symbol=symbol)
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except TypeError as e:
            logger.warning(f"AKShare futures_open_interest TypeError: {e}")
            return AdapterResult(
                data=None,
                error=f"TypeError: {e}",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare futures_open_interest 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def exchange_rank(self, exchange: str, date: Optional[str] = None) -> AdapterResult:
        """
        获取交易所持仓排名
        
        Parameters:
        -----------
        exchange: 交易所代码 (如 "SHFE", "DCE")
        date: 日期 (可选)
        
        Returns:
        --------
        AdapterResult
        """
        try:
            today_str = date if date else datetime.now().strftime("%Y%m%d")
            df = ak.get_shfe_rank_table(date=today_str)
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare exchange_rank 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def bond_yield(self, bond_type: str = "US10Y") -> AdapterResult:
        """
        获取国债收益率
        
        Parameters:
        -----------
        bond_type: 债券类型
            - "US10Y": 美国10年期国债收益率
            - "US2Y": 美国2年期国债收益率
            - "CN10Y": 中国10年期国债收益率 (如果支持)
        
        Returns:
        --------
        AdapterResult
        """
        try:
            if "US" in bond_type.upper() or "10Y" in bond_type:
                df = ak.bond_zh_us_rate()
            else:
                # 默认使用美债
                df = ak.bond_zh_us_rate()
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare bond_yield 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def precious_metal_spot(self, metal: str = "AU") -> AdapterResult:
        """
        获取贵金属现货价格
        
        Parameters:
        -----------
        metal: 金属类型 ("AU", "AG", "AU_AG")
        
        Returns:
        --------
        AdapterResult
        """
        try:
            if metal == "AU":
                df = ak.spot_golden_benchmark_sge()
            elif metal == "AG":
                df = ak.spot_silver_benchmark_sge()
            else:
                # 默认返回黄金
                df = ak.spot_golden_benchmark_sge()
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare precious_metal_spot 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def macro_data(self, indicator: str, country: str = "US") -> AdapterResult:
        """
        获取宏观数据
        
        Parameters:
        -----------
        indicator: 指标名称
            - "CPI": 消费者物价指数
            - "NONFARM": 非农就业
            - "FED_RATE": 联邦基金利率
            - "DXY": 美元指数
        country: 国家 ("US", "CN", "EU")
        
        Returns:
        --------
        AdapterResult
        """
        try:
            if indicator == "CPI":
                df = ak.macro_usa_cpi_yoy()
            elif indicator == "NONFARM":
                df = ak.macro_usa_non_farm()
            elif indicator == "FED_RATE":
                df = ak.macro_bank_usa_interest_rate()
            elif indicator == "DXY":
                df = ak.macro_usa_dollar_index()
            else:
                return AdapterResult(
                    data=None,
                    error=f"未知指标: {indicator}",
                    source_name=self.name,
                    confidence=1.0,
                    is_success=False
                )
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare macro_data 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def lme_stock(self, metal: str) -> AdapterResult:
        """
        获取LME库存数据
        
        Parameters:
        -----------
        metal: 金属代码 (如 "AL", "CU", "ZN", "NI")
        
        Returns:
        --------
        AdapterResult
        """
        try:
            df = ak.macro_euro_lme_stock()
            if df is not None and not df.empty:
                # 筛选指定金属
                metal_upper = metal.upper()
                if '品种' in df.columns:
                    df = df[df['品种'].str.upper().str.contains(metal_upper, na=False)]
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare lme_stock 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
    
    def warehouse_receipt(self, exchange: str, symbol: str, date: Optional[str] = None) -> AdapterResult:
        """
        获取仓单数据
        
        Parameters:
        -----------
        exchange: 交易所代码 (如 "SHFE", "DCE", "CZCE")
        symbol: 品种代码 (如 "AU", "AG", "CU")
        date: 日期 (可选)
        
        Returns:
        --------
        AdapterResult
        """
        try:
            if exchange.upper() == "SHFE":
                df = ak.futures_shfe_warehouse_receipt(symbol=symbol, date=date)
            elif exchange.upper() == "CZCE":
                df = ak.futures_warehouse_receipt_czce(symbol=symbol)
            else:
                # 尝试SHFE作为默认
                df = ak.futures_shfe_warehouse_receipt(symbol=symbol, date=date)
            
            if df is not None and not df.empty:
                return AdapterResult(
                    data=df,
                    error=None,
                    source_name=self.name,
                    confidence=1.0,
                    is_success=True
                )
            return AdapterResult(
                data=None,
                error="无数据返回",
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )
        except Exception as e:
            logger.warning(f"AKShare warehouse_receipt 失败: {e}")
            return AdapterResult(
                data=None,
                error=str(e),
                source_name=self.name,
                confidence=1.0,
                is_success=False
            )


# 单例实例
_akshare_adapter = AKShareAdapter()


def get_akshare_adapter() -> AKShareAdapter:
    """获取AKShare适配器单例"""
    return _akshare_adapter
