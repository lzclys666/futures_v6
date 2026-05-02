import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum
import sqlite3
import os
import sys

# 添加共享模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.data_access import PITDataService


class SignalStrength(Enum):
    """信号强度枚举"""
    STRONG_SELL = "STRONG_SELL"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"
    BUY = "BUY"
    STRONG_BUY = "STRONG_BUY"


class MarketRegime(Enum):
    """市场状态枚举"""
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"


class SignalScoringSystem:
    """
    信号评分系统
    
    功能：
    1. 多因子IC加权评分
    2. 信号强度分级
    3. 置信度计算
    4. 市场状态检测
    
    作者：因子分析师YIYI
    日期：2026-04-27
    """
    
    def __init__(self, data_path: str = None, db_path: str = None):
        """
        初始化
        
        Args:
            data_path: 数据根目录
            db_path: 参数数据库路径
        """
        self.data_service = PITDataService(data_path, db_path)
        
        print(f"[OK] SignalScoringSystem 初始化完成")
    
    def get_factor_params(self, symbol: str) -> List[Dict]:
        """
        从数据库获取品种的所有因子参数
        
        Args:
            symbol: 品种代码
        
        Returns:
            因子参数列表
        """
        return self.data_service.get_optimal_params(symbol)
    
    def load_factor_value(self, symbol: str, factor: str) -> Optional[float]:
        """
        加载因子最新值
        
        Args:
            symbol: 品种代码
            factor: 因子名称
        
        Returns:
            最新因子值
        """
        df = self.data_service.get_factor_snapshot(symbol, factor)
        
        if df.empty:
            return None
        
        # 返回最新值（最后一行的最后一列）
        latest = df.iloc[-1]
        
        # 尝试获取value列，如果不存在则获取最后一列
        if 'value' in latest:
            return float(latest['value'])
        elif 'au_ag_ratio_corrected' in latest:
            return float(latest['au_ag_ratio_corrected'])
        elif 'usd_cny' in latest:
            return float(latest['usd_cny'])
        else:
            # 获取最后一列（排除date列）
            value_cols = [c for c in df.columns if c != 'date']
            if value_cols:
                return float(latest[value_cols[-1]])
            return None
    
    def compute_signal_score(self, symbol: str) -> Dict:
        """
        计算信号评分
        
        Args:
            symbol: 品种代码
        
        Returns:
            信号评分字典
        """
        print(f"\n[1] 计算 {symbol} 信号评分...")
        
        # 获取因子参数
        factors = self.get_factor_params(symbol)
        
        if not factors:
            return {
                "symbol": symbol,
                "compositeScore": 50.0,
                "signalStrength": "NEUTRAL",
                "confidence": 0.0,
                "factorDetails": [],  # Lucy 要求：factorBreakdown → factorDetails
                "regime": "RANGING",
                "timestamp": datetime.now().isoformat() + "Z"
            }
        
        # 归一化IR作为权重
        ir_values = [f['ir'] for f in factors]
        ir_sum = sum(abs(ir) for ir in ir_values)
        
        if ir_sum == 0:
            weights = [1.0 / len(factors)] * len(factors)
        else:
            weights = [abs(ir) / ir_sum for ir in ir_values]
        
        # 计算每个因子的贡献
        factor_breakdown = []
        weighted_score = 0.0
        total_weight = 0.0
        
        for i, factor in enumerate(factors):
            # 加载因子最新值
            factor_value = self.load_factor_value(symbol, factor['factor'])
            
            if factor_value is None:
                continue
            
            # 根据IC均值确定方向
            ic_mean = factor['ic_mean']
            
            # 标准化因子值到0-100分
            # 假设因子值范围在-3到+3个标准差之间
            normalized_score = 50.0 + (factor_value * 16.67)  # 映射到0-100
            normalized_score = max(0.0, min(100.0, normalized_score))
            
            # 根据IC方向调整
            if ic_mean < 0:
                # 负IC因子，反转信号
                normalized_score = 100.0 - normalized_score
            
            # 计算贡献
            weight = weights[i]
            contribution = normalized_score * weight
            
            factor_breakdown.append({
                "factorName": factor['factor'],
                "weight": round(weight, 4),
                "ic": round(ic_mean, 4),
                "contribution": round(contribution, 2),
                "rawValue": round(factor_value, 4)
            })
            
            weighted_score += contribution
            total_weight += weight
        
        # 计算综合评分
        if total_weight > 0:
            composite_score = weighted_score / total_weight
        else:
            composite_score = 50.0
        
        # 限制在0-100范围内
        composite_score = max(0.0, min(100.0, composite_score))
        
        # 确定信号强度
        signal_strength = self._score_to_signal(composite_score)
        
        # 计算置信度
        confidence = self._compute_confidence(factors)
        
        # 检测市场状态
        regime = self._detect_regime(symbol)
        
        result = {
            "symbol": symbol,
            "compositeScore": round(composite_score, 2),
            "signalStrength": signal_strength.value,
            "confidence": round(confidence, 2),
            "factorDetails": factor_breakdown,  # Lucy 要求：factorBreakdown → factorDetails
            "regime": regime.value,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        print(f"  [OK] 评分完成: {composite_score:.2f} ({signal_strength.value})")
        
        return result
    
    def _score_to_signal(self, score: float) -> SignalStrength:
        """
        将分数转换为信号强度
        
        Args:
            score: 0-100的分数
        
        Returns:
            信号强度枚举
        """
        if score < 20:
            return SignalStrength.STRONG_SELL
        elif score < 40:
            return SignalStrength.SELL
        elif score < 60:
            return SignalStrength.NEUTRAL
        elif score < 80:
            return SignalStrength.BUY
        else:
            return SignalStrength.STRONG_BUY
    
    def _compute_confidence(self, factors: List[Dict]) -> float:
        """
        计算置信度
        
        基于：
        1. 因子数量
        2. 平均IR
        3. 平均胜率
        
        Args:
            factors: 因子列表
        
        Returns:
            置信度(0-100)
        """
        if not factors:
            return 0.0
        
        # 因子数量得分（最多10个因子得满分）
        count_score = min(len(factors) / 10.0, 1.0) * 30.0
        
        # 平均IR得分
        avg_ir = np.mean([abs(f['ir']) for f in factors])
        ir_score = min(avg_ir / 0.5, 1.0) * 40.0  # IR=0.5得满分
        
        # 平均胜率得分
        avg_win_rate = np.mean([f['win_rate'] for f in factors if f['win_rate']])
        win_rate_score = (avg_win_rate - 0.5) / 0.5 * 30.0  # 胜率50%得0分，100%得30分
        
        confidence = count_score + ir_score + win_rate_score
        return max(0.0, min(100.0, confidence))
    
    def _detect_regime(self, symbol: str) -> MarketRegime:
        """
        检测市场状态
        
        简单实现：基于价格波动率
        
        Args:
            symbol: 品种代码
        
        Returns:
            市场状态枚举
        """
        # 加载价格数据
        df = self.data_service.get_price_snapshot(symbol)
        
        if df.empty or len(df) < 20:
            return MarketRegime.RANGING
        
        # 计算波动率（最近20天）
        recent = df.tail(20)
        returns = recent['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # 年化波动率
        
        # 计算趋势强度
        price_range = (recent['close'].max() - recent['close'].min()) / recent['close'].mean()
        
        # 判断状态
        if volatility > 0.5:  # 高波动
            return MarketRegime.HIGH_VOLATILITY
        elif price_range > 0.1:  # 强趋势
            return MarketRegime.TRENDING
        else:
            return MarketRegime.RANGING
    
    def batch_compute_signals(self, symbols: List[str]) -> List[Dict]:
        """
        批量计算信号
        
        Args:
            symbols: 品种列表
        
        Returns:
            信号列表
        """
        signals = []
        
        for symbol in symbols:
            signal = self.compute_signal_score(symbol)
            signals.append(signal)
        
        return signals


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 80)
    print("信号评分系统测试")
    print("=" * 80)
    
    # 初始化评分系统
    scoring = SignalScoringSystem()
    
    # 测试品种
    test_symbols = ['RB', 'I', 'AU']
    
    # 计算信号
    for symbol in test_symbols:
        result = scoring.compute_signal_score(symbol)
        
        print("\n" + "-" * 80)
        print(f"品种: {result['symbol']}")
        print(f"综合评分: {result['compositeScore']}")
        print(f"信号强度: {result['signalStrength']}")
        print(f"置信度: {result['confidence']}%")
        print(f"市场状态: {result['regime']}")
        
        if result['factorBreakdown']:
            print("\n因子分解:")
            for factor in result['factorBreakdown']:
                print(f"  {factor['factorName']}: 权重={factor['weight']:.2%}, "
                      f"IC={factor['ic']:+.4f}, 贡献={factor['contribution']:.2f}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
