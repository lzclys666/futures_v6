# core/normalizer/robust_normalizer.py
import numpy as np
from typing import List
from datetime import date

class MADNormalizer:
    """MAD标准化器，支持差分EMA（日频）和HP滤波（月频）"""
    
    def __init__(self):
        pass
    
    def normalize(self, factor_code: str, symbol: str, raw_value: float,
                  as_of_date: date, window_data: List[float]) -> float:
        """
        返回标准化后的因子得分（-3~3）
        """
        if len(window_data) < 30:
            return 0.0  # 数据不足，返回中性
        
        # 1. 去趋势处理（简化版：日频用差分，月频暂不处理）
        # 实际应根据元数据判断频率，这里先统一用原始值
        values = np.array(window_data)
        
        # 2. MAD标准化
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        if mad == 0:
            norm_score = 0.0
        else:
            norm_score = (raw_value - median) / mad
        
        # 3. 截断到 [-3, 3]
        norm_score = max(-3.0, min(3.0, norm_score))
        
        return norm_score