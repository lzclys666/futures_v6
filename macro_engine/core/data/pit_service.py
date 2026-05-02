# core/data/pit_service.py
"""
PIT (Point-in-Time) 数据服务层
严格按“当时已知”原则提供因子数据，杜绝未来信息泄露。
兼容爬虫生成的 pit_data.db 表结构（obs_date）。
"""
import sqlite3
import json
from datetime import date
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class PitDataService:
    """PIT 数据服务，负责从数据库提取因子观测值和元数据"""

    def __init__(self, db_path: str = None, redis_client=None):
        """
        初始化数据服务
        :param db_path: 数据库文件路径，若不指定则自动探测
        :param redis_client: Redis 客户端实例，用于缓存历史窗口数据（可选）
        """
        if db_path is None:
            # 优先使用根目录的 pit_data.db（爬虫写入），若不存在则回退到 db/pit_factors.db
            root_db = Path(__file__).parent.parent.parent / "pit_data.db"
            if root_db.exists():
                db_path = str(root_db)
            else:
                db_path = str(Path(__file__).parent.parent.parent / "db" / "pit_factors.db")
        self.db_path = db_path
        self.redis = redis_client

    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    # ==================== 因子观测值查询 ====================

    def get_snapshot(self, symbol: str, as_of_date: date) -> Dict[str, Tuple[float, float]]:
        """
        获取指定日期开盘前已发布的所有因子最新值
        :param symbol: 品种代码（如 'RU'）
        :param as_of_date: 截止日期（PIT 原则，只返回 obs_date <= as_of_date 的数据）
        :return: {factor_code: (raw_value, source_confidence)}
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        # 子查询：每个因子在 as_of_date 之前的最新 obs_date
        query = '''
        SELECT factor_code, raw_value, source_confidence
        FROM pit_factor_observations
        WHERE symbol = ? AND obs_date <= ?
        GROUP BY factor_code
        HAVING obs_date = MAX(obs_date)
        '''
        cursor.execute(query, (symbol, as_of_date.isoformat()))
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: (row[1], row[2]) for row in rows}

    def get_window(self, factor_code: str, symbol: str, as_of_date: date, window: int) -> List[float]:
        """
        获取用于标准化的滚动窗口数据（PIT 对齐）
        :param factor_code: 因子代码
        :param symbol: 品种代码
        :param as_of_date: 截止日期
        :param window: 窗口大小（返回最近 window 条数据）
        :return: 历史观测值列表（按时间升序）
        """
        # 1. 尝试从 Redis 读取缓存
        if self.redis:
            cache_key = f"pit:window:{factor_code}:{symbol}"
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # 2. 缓存未命中，查询数据库
        conn = self._get_conn()
        cursor = conn.cursor()
        query = '''
        SELECT raw_value FROM pit_factor_observations
        WHERE factor_code = ? AND symbol = ? AND obs_date <= ?
        ORDER BY obs_date DESC
        LIMIT ?
        '''
        cursor.execute(query, (factor_code, symbol, as_of_date.isoformat(), window))
        rows = cursor.fetchall()
        conn.close()

        values = [row[0] for row in rows][::-1]  # 反转为时间升序

        # 3. 写入 Redis 缓存（24 小时过期）
        if self.redis and values:
            self.redis.setex(cache_key, 86400, json.dumps(values))

        return values

    def get_latest(self, symbol: str) -> Dict[str, Tuple[float, float]]:
        """获取最新可用的因子值（实盘使用）"""
        return self.get_snapshot(symbol, date.today())

    # ==================== 因子元数据查询 ====================

    def get_factor_metadata(self, factor_code: str) -> Dict:
        """
        获取单个因子的元数据
        :return: 至少包含 'factor_code', 'direction', 'frequency'
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM factor_metadata WHERE factor_code = ?', (factor_code,))
        row = cursor.fetchone()
        conn.close()
        if row:
            # 假设字段顺序：factor_code, factor_name, econ_category, logic_category, direction, frequency, ...
            return {
                'factor_code': row[0],
                'direction': row[4] if len(row) > 4 else 1,
                'frequency': row[5] if len(row) > 5 else 'daily'
            }
        return {}

    def get_active_factors(self, symbol: str) -> List[str]:
        """
        获取某品种当前启用的所有因子代码
        注：当前实现暂不区分品种，返回全部启用的因子
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT factor_code FROM factor_metadata WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows] if rows else []

    # ==================== 数据写入（供爬虫或管理后台使用） ====================

    def insert_observation(self, factor_code: str, symbol: str, obs_date: date,
                           raw_value: float, source: str = "manual", confidence: float = 1.0):
        """插入或替换一条因子观测值"""
        conn = self._get_conn()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute('''
        INSERT OR REPLACE INTO pit_factor_observations
        (factor_code, symbol, obs_date, pub_date, raw_value, source, source_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (factor_code, symbol, obs_date.isoformat(), today, raw_value, source, confidence))
        conn.commit()
        conn.close()

    def upsert_metadata(self, factor_code: str, factor_name: str, direction: int,
                        frequency: str = 'daily', norm_method: str = 'mad', is_active: int = 1):
        """插入或更新因子元数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO factor_metadata
        (factor_code, factor_name, direction, frequency, norm_method, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (factor_code, factor_name, direction, frequency, norm_method, is_active))
        conn.commit()
        conn.close()