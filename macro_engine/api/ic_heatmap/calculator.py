import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sqlite3
import os
import sys

# 添加共享模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.data_access import PITDataService

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'pit_data.db')

class ICHeatmapCalculator:
    """
    IC热力图计算模块
    
    功能：
    1. 计算多品种多因子的IC矩阵
    2. 支持滚动窗口计算
    3. 输出标准化JSON格式
    
    作者：因子分析师YIYI
    日期：2026-04-27
    """
    
    def __init__(self, data_path: str = None):
        """
        初始化
        
        Args:
            data_path: 数据根目录，默认使用配置路径
        """
        self.data_service = PITDataService(data_path)
        
        # 默认因子列表
        self.default_factors = [
            'basis', 'spread', 'hold_volume', 'basis_volatility', 'import'
        ]
        
        # 因子配置（suffix + value_col，运行时拼接 symbol 前缀）
        self.factor_config = {
            "basis": {
                "suffix": "futures_basis",
                "value_col": "basis_rate",
                "has_contract": True,
            },
            "spread": {
                "suffix": "futures_spread",
                "value_col": "spread_01",
                "has_contract": False,
            },
            "hold_volume": {
                "suffix": "futures_hold_volume",
                "value_col": "hold_volume",
                "has_contract": True,
            },
            "basis_volatility": {
                "suffix": "basis_volatility",
                "value_col": "basis_vol_20d",
                "has_contract": False,
            },
            "import": {
                "suffix": "import_monthly",
                "value_col": "import_volume",
                "has_contract": False,
            },
        }
        
        # 表名解析方法
        self._get_table = lambda symbol, factor: f"{symbol.lower()}_{self.factor_config[factor]['suffix']}" if factor in self.factor_config else None
        
        print(f"[OK] ICHeatmapCalculator 初始化完成")
    
    def load_factor_data(self, symbol: str, factor: str) -> pd.Series:
        """
        从数据库加载因子数据
        
        Args:
            symbol: 品种代码，如 'JM'
            factor: 因子名称，如 'basis'
        
        Returns:
            因子数据Series，index为日期
        """
        config = self.factor_config.get(factor)
        if not config:
            print(f"  [错误] 未知因子: {factor}")
            return pd.Series()
        
        table_name = self._get_table(symbol, factor)
        
        conn = sqlite3.connect(DB_PATH)
        
        # 检查表是否存在
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            print(f"  [警告] 表不存在: {table_name}")
            conn.close()
            return pd.Series()
        
        # 构建查询
        if config['has_contract']:
            where_clause = f"WHERE contract LIKE '{symbol}%'"
        else:
            where_clause = ""
        
        query = f"""
            SELECT obs_date, {config['value_col']} as value
            FROM {table_name}
            {where_clause}
            ORDER BY obs_date
        """
        
        try:
            df = pd.read_sql_query(query, conn)
            print(f"  [数据] {factor}: 从 {table_name} 读取 {len(df)} 条记录")
        except Exception as e:
            print(f"  [错误] 查询失败: {e}")
            conn.close()
            return pd.Series()
        
        conn.close()
        
        if df.empty:
            print(f"  [警告] {factor}: 无数据")
            return pd.Series()
        
        df['obs_date'] = pd.to_datetime(df['obs_date'])
        df = df.set_index('obs_date').sort_index()
        df = df.groupby(df.index).mean(numeric_only=True)
        df = df.dropna()
        
        print(f"  [数据] {factor}: 有效数据 {len(df)} 条")
        
        # 返回第一列（数值列）
        if len(df.columns) > 0:
            return df.iloc[:, 0]
        return pd.Series()
    
    def load_price_data(self, symbol: str) -> pd.Series:
        """
        从数据库加载价格数据
        
        Args:
            symbol: 品种代码
        
        Returns:
            价格数据Series
        """
        conn = sqlite3.connect(DB_PATH)
        
        # 各品种共用 jm_futures_ohlcv（contract 为 {symbol}0）
        query = f"""
            SELECT obs_date, close
            FROM jm_futures_ohlcv
            WHERE contract = '{symbol}0'
            ORDER BY obs_date
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return pd.Series()
        
        df['obs_date'] = pd.to_datetime(df['obs_date'])
        df = df.set_index('obs_date').sort_index()
        
        return df['close']
    
    def compute_forward_return(self, price: pd.Series, hold_period: int = 5) -> pd.Series:
        """
        计算forward return
        
        Args:
            price: 价格序列
            hold_period: 持有期天数
        
        Returns:
            forward return序列
        """
        return price.pct_change(hold_period).shift(-hold_period)
    
    def load_ic_from_db(self, symbol: str, factor: str) -> float:
        """
        从数据库读取预计算的 IC 值
        
        Args:
            symbol: 品种代码
            factor: 因子名称
        
        Returns:
            IC值，如果没有则返回 None
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ic_value, is_mock 
            FROM ic_heatmap 
            WHERE symbol = ? AND factor = ?
            ORDER BY calc_date DESC 
            LIMIT 1
        """, (symbol, factor))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None

    def compute_ic(self, factor: pd.Series, forward_return: pd.Series, 
                   lookback: int = 60, symbol: str = None, factor_name: str = None) -> float:
        """
        计算IC（Spearman相关系数）
        
        Args:
            factor: 因子序列
            forward_return: 前瞻收益序列
            lookback: 回看窗口天数
        
        Returns:
            IC值
        """
        # 对齐数据
        aligned = pd.DataFrame({
            'factor': factor,
            'return': forward_return
        }).dropna()
        
        print(f"    [计算] 对齐后数据: {len(aligned)} 条")
        
        if len(aligned) < 20:  # 最小样本数要求
            print(f"    [警告] 数据不足 ({len(aligned)} < 20)，返回 NaN")
            return np.nan
        
        # 取最近lookback天
        recent = aligned.tail(lookback)
        
        # 计算Spearman IC
        ic, pvalue = spearmanr(recent['factor'], recent['return'])
        
        print(f"    [计算] IC={ic:.4f}, p-value={pvalue:.4f}, 样本数={len(recent)}")
        
        return ic if not np.isnan(ic) else 0.0
    
    def compute_ic_matrix(self, symbols: List[str], factors: List[str],
                         lookback: int = 60, hold_period: int = 5) -> Dict:
        """
        计算IC热力图矩阵
        
        Args:
            symbols: 品种列表
            factors: 因子列表
            lookback: 回看天数
            hold_period: 持有期天数
        
        Returns:
            IC矩阵字典，符合API响应格式
        """
        print(f"\n[1] 开始计算IC矩阵...")
        print(f"  品种: {symbols}")
        print(f"  因子: {factors}")
        print(f"  回看: {lookback}天")
        print(f"  持有: {hold_period}天")
        
        # 初始化矩阵
        ic_matrix = []
        
        # 对每个因子计算IC
        for factor in factors:
            ic_row = []
            
            for symbol in symbols:
                # 加载因子数据
                factor_data = self.load_factor_data(symbol, factor)
                
                # 加载价格数据
                price_data = self.load_price_data(symbol)
                
                if len(factor_data) == 0 or len(price_data) == 0:
                    ic_row.append(0.0)
                    continue
                
                # 计算forward return
                fwd_return = self.compute_forward_return(price_data, hold_period)
                
                # 计算IC
                ic = self.compute_ic(factor_data, fwd_return, lookback, symbol, factor)
                ic_row.append(round(ic, 4) if not np.isnan(ic) else 0.0)
            
            ic_matrix.append(ic_row)
        
        # 构建响应
        result = {
            "factors": factors,
            "symbols": symbols,
            "icMatrix": ic_matrix,
            "lookbackPeriod": lookback,
            "holdPeriod": hold_period,
            "updatedAt": datetime.now().isoformat() + "Z"
        }
        
        print(f"\n[OK] IC矩阵计算完成")
        print(f"  矩阵大小: {len(factors)} x {len(symbols)}")
        
        return result
    
    def get_optimal_params(self, symbol: str) -> Dict:
        """
        从数据库获取最优参数
        
        Args:
            symbol: 品种代码
        
        Returns:
            最优参数字典
        """
        params = self.data_service.get_optimal_params(symbol)
        
        if params:
            best = params[0]
            return {
                'factor': best['factor'],
                'ic_window': best['ic_window'],
                'hold_period': best['hold_period'],
                'weight': best['weight'],
                'ir': best['ir']
            }
        
        # 默认参数
        return {
            'factor': 'momentum',
            'ic_window': 60,
            'hold_period': 5,
            'weight': 1.0,
            'ir': 0.0
        }
    
    def compute_heatmap_with_optimal_params(self, symbols: List[str]) -> Dict:
        """
        使用最优参数计算IC热力图
        
        Args:
            symbols: 品种列表
        
        Returns:
            IC矩阵字典
        """
        # 获取所有品种的最优因子
        all_factors = set()
        symbol_params = {}
        
        for symbol in symbols:
            params = self.get_optimal_params(symbol)
            symbol_params[symbol] = params
            all_factors.add(params['factor'])
        
        # 使用统一的lookback（取中位数）
        lookbacks = [p['ic_window'] for p in symbol_params.values()]
        lookback = int(np.median(lookbacks))
        
        # 使用统一的hold_period（取中位数）
        hold_periods = [p['hold_period'] for p in symbol_params.values()]
        hold_period = int(np.median(hold_periods))
        
        # 计算IC矩阵
        return self.compute_ic_matrix(
            symbols=symbols,
            factors=list(all_factors),
            lookback=lookback,
            hold_period=hold_period
        )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 80)
    print("IC热力图计算模块测试")
    print("=" * 80)
    
    # 初始化计算器
    calculator = ICHeatmapCalculator()
    
    # 测试品种
    test_symbols = ['JM', 'RU', 'RB', 'ZN', 'NI']
    
    # 测试因子
    test_factors = ['basis', 'spread', 'hold_volume']
    
    # 计算IC矩阵
    result = calculator.compute_ic_matrix(
        symbols=test_symbols,
        factors=test_factors,
        lookback=60,
        hold_period=5
    )
    
    # 打印结果
    print("\n" + "=" * 80)
    print("IC热力图结果")
    print("=" * 80)
    
    print(f"\n因子: {result['factors']}")
    print(f"品种: {result['symbols']}")
    print(f"回看: {result['lookbackPeriod']}天")
    print(f"持有: {result['holdPeriod']}天")
    print(f"更新: {result['updatedAt']}")
    
    print("\nIC矩阵:")
    # 打印表头
    header = "因子\\品种".ljust(12)
    for symbol in result['symbols']:
        header += symbol.ljust(10)
    print(header)
    print("-" * 80)
    
    # 打印数据
    for i, factor in enumerate(result['factors']):
        row = factor.ljust(12)
        for j, symbol in enumerate(result['symbols']):
            ic_value = result['icMatrix'][i][j]
            # 根据IC值着色（简单文本表示）
            if ic_value > 0.1:
                row += f"{ic_value:+.4f}  "
            elif ic_value < -0.1:
                row += f"{ic_value:+.4f}  "
            else:
                row += f"{ic_value:+.4f}  "
        print(row)
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
