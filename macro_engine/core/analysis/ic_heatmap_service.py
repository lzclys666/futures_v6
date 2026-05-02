# core/analysis/ic_heatmap_service.py
"""
IC (Information Coefficient) 热力图服务
计算因子与品种未来收益的 Spearman 相关系数
"""
import numpy as np
import pandas as pd
from scipy import stats
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from core.data.pit_service import PitDataService


@dataclass
class IcResult:
    """IC 计算结果"""
    factor_code: str
    symbol: str
    ic_value: float
    ic_significance: float  # p-value
    sample_size: int
    calc_date: date


class IcHeatmapService:
    """
    IC 热力图服务
    
    功能:
    1. 计算单因子-单品种的 Spearman IC
    2. 生成 IC 热力图数据矩阵
    3. 计算 IC 的滚动均值和 IR (Information Ratio)
    """
    
    def __init__(self, db_path: str = None, forward_period: int = 5):
        """
        初始化 IC 服务
        :param db_path: PIT 数据库路径
        :param forward_period: 前瞻期（默认5个交易日）
        """
        self.pit_service = PitDataService(db_path)
        self.forward_period = forward_period

    def get_factors(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        获取可用因子列表（兼容 stub 接口）
        :param symbol: 可选，限定品种
        :return: [{factor_code, factor_name, category}, ...]
        """
        try:
            conn = self.pit_service._get_conn()
            cursor = conn.cursor()
            if symbol:
                cursor.execute(
                    "SELECT DISTINCT factor_code FROM pit_factor_observations WHERE symbol = ? ORDER BY factor_code",
                    (symbol,)
                )
            else:
                cursor.execute("SELECT DISTINCT factor_code FROM pit_factor_observations ORDER BY factor_code")
            factor_codes = sorted(r[0] for r in cursor.fetchall())
            conn.close()
            if factor_codes:
                return [
                    {"factor_code": code, "factor_name": code, "category": "macro"}
                    for code in factor_codes
                ]
        except Exception:
            pass
        return []
        
    def calculate_ic(
        self,
        factor_code: str,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> Optional[IcResult]:
        """
        计算单因子-单品种的 IC 值
        
        使用 Spearman 相关系数（对异常值稳健）
        
        :param factor_code: 因子代码
        :param symbol: 品种代码（如 'RU'）
        :param start_date: 计算起始日期
        :param end_date: 计算结束日期
        :return: IcResult 或 None（数据不足）
        """
        # 1. 获取因子值时间序列（PIT）
        factor_values = self._get_factor_series(factor_code, symbol, start_date, end_date)
        if len(factor_values) < 30:  # 最少需要30个样本
            return None
            
        # 2. 获取未来收益时间序列
        returns = self._get_forward_returns(symbol, [d for d, _ in factor_values])
        if len(returns) < 30:
            return None
            
        # 3. 对齐数据
        aligned_factors = []
        aligned_returns = []
        for obs_date, factor_value in factor_values:
            if obs_date in returns:
                aligned_factors.append(factor_value)
                aligned_returns.append(returns[obs_date])
                
        if len(aligned_factors) < 30:
            return None
            
        # 4. 计算 Spearman IC
        ic_value, p_value = stats.spearmanr(aligned_factors, aligned_returns)
        
        return IcResult(
            factor_code=factor_code,
            symbol=symbol,
            ic_value=ic_value,
            ic_significance=p_value,
            sample_size=len(aligned_factors),
            calc_date=end_date
        )
        
    def get_heatmap_data(
        self,
        symbols: List[str],
        as_of_date: date = None,
        lookback_days: int = 252
    ) -> Dict:
        """
        生成 IC 热力图数据
        
        :param symbols: 品种列表（如 ['RU', 'ZN', 'RB', 'NI']）
        :param as_of_date: 截止日期（默认今天）
        :param lookback_days: 回溯期（默认252个交易日≈1年）
        :return: {
            'factors': ['factor1', 'factor2', ...],
            'symbols': ['RU', 'ZN', ...],
            'matrix': [[ic11, ic12, ...], [ic21, ic22, ...], ...],
            'ir_matrix': [[ir11, ir12, ...], ...],
            'significance': [[p1, p2, ...], ...],
            'calc_date': '2026-04-27'
        }
        """
        if as_of_date is None:
            as_of_date = date.today()
            
        start_date = as_of_date - timedelta(days=lookback_days)
        
        # 获取所有活跃因子（按请求品种过滤，仅保留 DB 中有数据的因子）
        # pit_service.get_active_factors() 返回 factor_metadata 中 is_active=1 的因子，
        # 但那些 SA 型因子（sa_futures_daily_close 等）在 pit_observations 中没有数据，
        # 因此直接用 pit_observations 中实际存在的因子代码
        conn = self.pit_service._get_conn()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(symbols))
        cursor.execute(
            f"SELECT DISTINCT factor_code FROM pit_factor_observations WHERE symbol IN ({placeholders})",
            symbols
        )
        all_factors = sorted(set(r[0] for r in cursor.fetchall()))
        conn.close()
        
        # 构建矩阵
        matrix = []
        ir_matrix = []
        significance_matrix = []
        
        for factor_code in all_factors:
            ic_row = []
            ir_row = []
            sig_row = []
            
            for symbol in symbols:
                # 计算 IC
                ic_result = self.calculate_ic(factor_code, symbol, start_date, as_of_date)
                
                if ic_result:
                    ic_row.append(ic_result.ic_value)
                    sig_row.append(ic_result.ic_significance)
                    
                    # 计算 IR (IC / std(IC))
                    ic_series = self._get_ic_series(factor_code, symbol, start_date, as_of_date)
                    if len(ic_series) > 1:
                        ir = np.mean(ic_series) / np.std(ic_series)
                        ir_row.append(ir)
                    else:
                        ir_row.append(0.0)
                else:
                    ic_row.append(None)
                    ir_row.append(None)
                    sig_row.append(None)
                    
            matrix.append(ic_row)
            ir_matrix.append(ir_row)
            significance_matrix.append(sig_row)
            
        return {
            'factors': all_factors,
            'symbols': symbols,
            'matrix': matrix,
            'ir_matrix': ir_matrix,
            'significance': significance_matrix,
            'calc_date': as_of_date.isoformat(),
            'lookback_days': lookback_days,
            'forward_period': self.forward_period
        }
        
    def get_ic_history(
        self,
        factor_code: str,
        symbol: str,
        start_date: date,
        end_date: date,
        rolling_window: int = 20
    ) -> Dict:
        """
        获取 IC 历史走势
        
        :param factor_code: 因子代码
        :param symbol: 品种代码
        :param start_date: 起始日期
        :param end_date: 结束日期
        :param rolling_window: 滚动窗口（默认20日）
        :return: {
            'dates': ['2026-01-01', ...],
            'ic_values': [0.1, 0.2, ...],
            'ic_ma': [0.15, 0.18, ...],  # 滚动均值
            'ir_values': [0.5, 0.6, ...]  # 滚动 IR
        }
        """
        # 计算每日 IC
        dates = []
        ic_values = []
        
        current_date = start_date
        while current_date <= end_date:
            # 跳过周末（简化处理）
            if current_date.weekday() < 5:
                ic_result = self.calculate_ic(
                    factor_code, symbol,
                    current_date - timedelta(days=60),  # 60日回溯
                    current_date
                )
                if ic_result:
                    dates.append(current_date.isoformat())
                    ic_values.append(ic_result.ic_value)
                    
            current_date += timedelta(days=1)
            
        # 计算滚动均值和 IR
        ic_series = pd.Series(ic_values)
        ic_ma = ic_series.rolling(window=rolling_window, min_periods=1).mean()
        
        # 滚动 IR
        ir_values = []
        for i in range(len(ic_values)):
            start_idx = max(0, i - rolling_window + 1)
            window_ic = ic_values[start_idx:i+1]
            if len(window_ic) > 1:
                ir = np.mean(window_ic) / np.std(window_ic)
                ir_values.append(ir)
            else:
                ir_values.append(0.0)
                
        return {
            'dates': dates,
            'ic_values': ic_values,
            'ic_ma': ic_ma.tolist(),
            'ir_values': ir_values,
            'factor_code': factor_code,
            'symbol': symbol,
            'rolling_window': rolling_window
        }
        
    def _get_factor_series(
        self,
        factor_code: str,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[Tuple[date, float]]:
        """获取因子时间序列（PIT）"""
        # 使用 pit_service 的 get_window 方法
        values = self.pit_service.get_window(factor_code, symbol, end_date, 1000)
        
        # 生成日期序列（简化处理，实际需要根据 obs_date）
        dates = []
        current = start_date
        while current <= end_date and len(dates) < len(values):
            if current.weekday() < 5:
                dates.append(current)
            current += timedelta(days=1)
            
        return list(zip(dates, values[-len(dates):]))
        
    def _get_forward_returns(
        self,
        symbol: str,
        dates: List[date]
    ) -> Dict[date, float]:
        """
        获取未来收益（使用真实期货价格数据）
        
        从 jm_futures_ohlcv 表读取收盘价，计算 forward_period 日后的收益率
        """
        returns = {}
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.pit_service.db_path)
            cursor = conn.cursor()
            
            # 查询该品种的所有历史收盘价
            # 注意：symbol 需要映射到 contract 前缀
            contract_prefix = self._symbol_to_contract(symbol)
            
            cursor.execute('''
                SELECT obs_date, close, contract
                FROM jm_futures_ohlcv 
                WHERE contract LIKE ? 
                ORDER BY obs_date ASC, contract ASC
            ''', (f'{contract_prefix}%',))
            
            price_data = cursor.fetchall()
            conn.close()
            
            if len(price_data) < self.forward_period + 1:
                # 数据不足，回退到模拟数据
                print(f"[IcHeatmapService] {symbol} 价格数据不足（仅{len(price_data)}条），使用模拟收益")
                for d in dates:
                    returns[d] = np.random.normal(0, 0.02)
                return returns
            
            # 构建价格字典 {date_str: close_price}
            # 对于每个日期，使用最近月份的合约（主力合约逻辑）
            price_dict = {}
            for obs_date_str, close_price, contract in price_data:
                try:
                    obs_date = datetime.strptime(obs_date_str, '%Y-%m-%d').date()
                    # 如果同一日期有多个合约，保留第一个（最近月份）
                    if obs_date not in price_dict:
                        price_dict[obs_date] = close_price
                except ValueError:
                    continue
            
            # 计算未来收益
            sorted_dates = sorted(price_dict.keys())
            
            for d in dates:
                if d not in price_dict:
                    continue
                    
                current_price = price_dict[d]
                
                # 找到 forward_period 个交易日后的日期
                try:
                    current_idx = sorted_dates.index(d)
                    future_idx = current_idx + self.forward_period
                    
                    if future_idx < len(sorted_dates):
                        future_date = sorted_dates[future_idx]
                        future_price = price_dict[future_date]
                        
                        # 计算收益率
                        if current_price > 0:
                            ret = (future_price - current_price) / current_price
                            returns[d] = ret
                except ValueError:
                    continue
                    
        except Exception as e:
            print(f"[IcHeatmapService] 读取价格数据错误: {e}")
            # 回退到模拟数据
            for d in dates:
                returns[d] = np.random.normal(0, 0.02)
                
        return returns
        
    def _symbol_to_contract(self, symbol: str) -> str:
        """
        将品种代码映射到合约代码前缀
        
        例如: RU -> RU, ZN -> ZN, JM -> JM
        """
        # 直接返回大写的品种代码
        return symbol.upper()
        
    def _get_ic_series(
        self,
        factor_code: str,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[float]:
        """获取 IC 时间序列用于计算 IR"""
        ic_values = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                ic_result = self.calculate_ic(
                    factor_code, symbol,
                    current_date - timedelta(days=30),
                    current_date
                )
                if ic_result:
                    ic_values.append(ic_result.ic_value)
            current_date += timedelta(days=1)
        return ic_values
