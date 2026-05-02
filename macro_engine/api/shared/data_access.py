"""
数据访问层 (Data Access Layer)

提供统一的数据访问接口，封装底层数据读取逻辑

作者：因子分析师YIYI
日期：2026-04-27
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from typing import Optional, List, Dict
from datetime import datetime


class PITDataService:
    """
    PIT (Point-in-Time) 数据服务
    
    提供PIT合规的数据访问，确保不使用未来数据
    """
    
    def __init__(self, data_path: str = None, db_path: str = None):
        """
        初始化PIT数据服务
        
        Args:
            data_path: 数据根目录
            db_path: 参数数据库路径
        """
        if data_path is None:
            self.data_path = r'D:\futures_v6\macro_engine\data\crawlers'
        else:
            self.data_path = data_path
        
        if db_path is None:
            self.db_path = r'D:\futures_v6\macro_engine\data\parameter_db.db'
        else:
            self.db_path = db_path
    
    def get_factor_snapshot(self, symbol: str, factor: str, 
                           as_of_date: datetime = None) -> pd.DataFrame:
        """
        获取因子快照（PIT合规）
        
        搜索顺序：
        1. 品种目录: data/crawlers/{symbol}/daily/{factor}.csv
        2. 共享目录: data/crawlers/_shared/daily/{factor}.csv
        3. 共享目录: data/crawlers/shared/daily/{factor}.csv
        
        Args:
            symbol: 品种代码
            factor: 因子名称
            as_of_date: 截止日期，None表示最新
        
        Returns:
            因子数据DataFrame
        """
        # 搜索路径列表
        search_paths = [
            # 1. 品种目录
            os.path.join(self.data_path, symbol, 'daily', f'{factor}.csv'),
            # 2. _shared目录
            os.path.join(self.data_path, '_shared', 'daily', f'{factor}.csv'),
            # 3. shared目录
            os.path.join(self.data_path, 'shared', 'daily', f'{factor}.csv'),
        ]
        
        # 查找存在的文件
        factor_path = None
        for path in search_paths:
            if os.path.exists(path):
                factor_path = path
                break
        
        # 如果找不到，记录日志并返回空
        if factor_path is None:
            # print(f"  [WARN] Factor file not found for {symbol}/{factor}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(factor_path)
            df['date'] = pd.to_datetime(df['date'])
            
            # PIT过滤：只返回as_of_date之前的数据
            if as_of_date is not None:
                df = df[df['date'] <= as_of_date]
            
            return df.sort_values('date')
        except Exception as e:
            print(f"  [ERROR] Failed to load factor {factor} for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_price_snapshot(self, symbol: str, 
                          as_of_date: datetime = None) -> pd.DataFrame:
        """
        获取价格快照（PIT合规）
        
        Args:
            symbol: 品种代码
            as_of_date: 截止日期
        
        Returns:
            价格数据DataFrame
        """
        price_path = os.path.join(
            self.data_path, symbol, 'daily', f'{symbol}_fut_close.csv'
        )
        
        if not os.path.exists(price_path):
            return pd.DataFrame()
        
        df = pd.read_csv(price_path)
        df['date'] = pd.to_datetime(df['date'])
        
        if as_of_date is not None:
            df = df[df['date'] <= as_of_date]
        
        return df.sort_values('date')
    
    def get_optimal_params(self, symbol: str) -> List[Dict]:
        """
        获取品种的最优参数
        
        Args:
            symbol: 品种代码
        
        Returns:
            参数列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT variety, factor, ic_window, hold_period, 
                       weight_decay, ir, ic_mean, win_rate
                FROM optimal_parameters
                WHERE variety = ? AND weight_decay > 0
                ORDER BY ir DESC
            ''', (symbol,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'variety': row[0],
                    'factor': row[1],
                    'ic_window': row[2],
                    'hold_period': row[3],
                    'weight': row[4],
                    'ir': row[5],
                    'ic_mean': row[6],
                    'win_rate': row[7]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[ERROR] 获取参数失败: {e}")
            return []
    
    def get_all_varieties(self) -> List[str]:
        """
        获取所有品种列表
        
        Returns:
            品种代码列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT variety FROM optimal_parameters
                ORDER BY variety
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in rows]
        except:
            # 默认品种列表
            return ['RB', 'HC', 'I', 'J', 'JM', 'AU', 'AG', 'CU', 'AL']


class DataValidator:
    """
    数据验证器
    
    验证数据质量和完整性
    """
    
    @staticmethod
    def validate_factor_data(df: pd.DataFrame) -> Dict:
        """
        验证因子数据
        
        Args:
            df: 因子数据
        
        Returns:
            验证结果
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        if df.empty:
            result['is_valid'] = False
            result['errors'].append('数据为空')
            return result
        
        # 检查必要列
        if 'date' not in df.columns:
            result['is_valid'] = False
            result['errors'].append('缺少date列')
        
        # 检查缺失值
        if df.isnull().any().any():
            result['warnings'].append('存在缺失值')
        
        # 检查重复日期
        if df['date'].duplicated().any():
            result['warnings'].append('存在重复日期')
        
        # 统计信息
        result['stats'] = {
            'row_count': len(df),
            'start_date': df['date'].min().strftime('%Y-%m-%d'),
            'end_date': df['date'].max().strftime('%Y-%m-%d'),
            'null_count': df.isnull().sum().sum()
        }
        
        return result
    
    @staticmethod
    def validate_price_data(df: pd.DataFrame) -> Dict:
        """
        验证价格数据
        
        Args:
            df: 价格数据
        
        Returns:
            验证结果
        """
        result = DataValidator.validate_factor_data(df)
        
        if not result['is_valid']:
            return result
        
        # 价格特有检查
        if 'close' in df.columns:
            close = df['close']
            
            # 检查负值
            if (close < 0).any():
                result['errors'].append('价格存在负值')
                result['is_valid'] = False
            
            # 检查零值
            if (close == 0).any():
                result['warnings'].append('价格存在零值')
            
            # 检查异常波动（单日涨跌超过20%）
            returns = close.pct_change()
            if (abs(returns) > 0.2).any():
                result['warnings'].append('存在异常波动（>20%）')
        
        return result


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 80)
    print("数据访问层测试")
    print("=" * 80)
    
    # 初始化服务
    service = PITDataService()
    
    # 测试获取品种列表
    varieties = service.get_all_varieties()
    print(f"\n[1] 品种列表: {varieties}")
    
    # 测试获取参数
    if varieties:
        params = service.get_optimal_params(varieties[0])
        print(f"\n[2] {varieties[0]} 参数:")
        for p in params[:3]:
            print(f"  {p['factor']}: IR={p['ir']:.4f}, 权重={p['weight']}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
