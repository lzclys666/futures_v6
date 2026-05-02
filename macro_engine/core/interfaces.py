# core/interfaces.py
from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Tuple, Optional, Any

class DataProvider(ABC):
    """数据提供者抽象接口"""
    
    @abstractmethod
    def get_snapshot(self, symbol: str, as_of_date: date) -> Dict[str, Tuple[float, float]]:
        """获取指定日期已发布的所有因子最新值，返回 {factor_code: (raw_value, confidence)}"""
        pass
    
    @abstractmethod
    def get_window(self, factor_code: str, symbol: str, as_of_date: date, window: int) -> List[float]:
        """获取用于标准化的滚动窗口数据（PIT对齐）"""
        pass
    
    @abstractmethod
    def get_factor_metadata(self, factor_code: str) -> Dict:
        """获取因子元数据"""
        pass
    
    @abstractmethod
    def get_active_factors(self, symbol: str) -> List[str]:
        """获取某品种当前启用的因子列表"""
        pass


class Normalizer(ABC):
    """标准化器抽象接口"""
    
    @abstractmethod
    def normalize(self, factor_code: str, symbol: str, raw_value: float,
                  as_of_date: date, window_data: List[float]) -> float:
        """返回标准化后的因子得分（-3~3）"""
        pass


class WeightCalculator(ABC):
    """权重计算器抽象接口"""
    
    @abstractmethod
    def calculate(self, symbol: str, factor_codes: List[str],
                  as_of_date: date, context: Dict) -> Dict[str, float]:
        """返回各因子的动态权重，总和为1.0"""
        pass


class FactorCalculator(ABC):
    """因子计算器抽象接口"""
    
    @abstractmethod
    def calculate(self, factor_code: str, context: Dict[str, Any]) -> float:
        """根据上下文计算原始因子值"""
        pass


class SentimentAnalyzer(ABC):
    """情感分析器抽象接口"""
    
    @abstractmethod
    def analyze(self, text: str) -> Dict[str, float]:
        """返回情感分析结果：{polarity, intensity, uncertainty}"""
        pass