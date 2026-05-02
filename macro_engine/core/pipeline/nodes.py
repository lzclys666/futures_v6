# core/pipeline/nodes.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.pipeline.base import PipelineNode
from core.normalizer.robust_normalizer import MADNormalizer
from core.scoring.weight_engine import WeightEngine
from typing import Dict, Any
import numpy as np


class NormalizeNode(PipelineNode):
    """因子标准化节点"""
    
    def __init__(self, normalizer=None, data_provider=None):
        self.normalizer = normalizer or MADNormalizer()
        self.data_provider = data_provider
    
    def process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context['symbol']
        as_of_date = context['as_of_date']
        raw_factors = data['raw_factors']
        
        normalized = {}
        for factor_code, raw_value in raw_factors.items():
            # 获取滚动窗口数据（简化处理，直接调用data_provider）
            window = self.data_provider.get_window(factor_code, symbol, as_of_date, window=756)
            score = self.normalizer.normalize(factor_code, symbol, raw_value, as_of_date, window)
            normalized[factor_code] = score
        
        data['normalized_factors'] = normalized
        return data


class OrthogonalizeNode(PipelineNode):
    """因子正交化节点（当前为简化版，直接透传）"""
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
    
    def process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # 简化版：不实际做正交化，直接复制
        normalized = data.get('normalized_factors', {})
        data['orthogonalized_factors'] = normalized.copy()
        data['factor_clusters'] = {f: 0 for f in normalized.keys()}
        return data


class WeightNode(PipelineNode):
    """动态加权节点"""
    
    def __init__(self, weight_calculator=None):
        self.weight_calculator = weight_calculator or WeightEngine()
    
    def process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context['symbol']
        # 优先使用正交化因子，如果没有则用标准化因子
        factors = data.get('orthogonalized_factors', data.get('normalized_factors', {}))
        factor_codes = list(factors.keys())
        
        weights = self.weight_calculator.calculate(symbol, factor_codes)
        data['weights'] = weights
        
        # 计算加权得分
        score = sum(factors[f] * weights.get(f, 0.0) for f in factors)
        # 映射到 0-100（简单线性映射）
        final_score = 50 + score * 15
        final_score = max(0, min(100, final_score))
        data['final_score'] = final_score
        return data


class DirectionNode(PipelineNode):
    """方向信号生成节点（含防抖，首次运行直接采纳）"""
    
    def __init__(self, thresholds=(40.0, 60.0), confirm_days=2):
        self.thresholds = thresholds
        self.confirm_days = confirm_days
        self.history = {}      # symbol -> (direction, count)
        self.first_run = {}    # 标记是否首次运行
    
    def process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context['symbol']
        score = data.get('final_score', 50.0)
        
        if score > self.thresholds[1]:
            raw_dir = "LONG"
        elif score < self.thresholds[0]:
            raw_dir = "SHORT"
        else:
            raw_dir = "NEUTRAL"
        
        # 首次运行直接采纳，不防抖
        if symbol not in self.first_run:
            self.first_run[symbol] = True
            self.history[symbol] = (raw_dir, self.confirm_days)  # 直接设为确认状态
            direction = raw_dir
        else:
            prev_dir, count = self.history.get(symbol, (None, 0))
            if raw_dir == prev_dir:
                count += 1
            else:
                count = 1
            self.history[symbol] = (raw_dir, count)
            direction = raw_dir if count >= self.confirm_days else (prev_dir if prev_dir else "NEUTRAL")
        
        data['direction'] = direction
        data['raw_direction'] = raw_dir
        data['score'] = score
        return data