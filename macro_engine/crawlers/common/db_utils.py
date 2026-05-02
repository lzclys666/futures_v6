"""
crawlers/common/db_utils.py
所有爬虫共享的数据库工具函数
"""

import sqlite3
import os
import time

# 数据库路径：统一从 common/ 向上两级到项目根目录
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pit_data.db")


def ensure_table():
    """确保 pit_factor_observations 表存在（含source列）"""
    conn = sqlite3.connect(DB_PATH)
    # 先检查source列是否存在，不存在则添加（兼容旧表）
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(pit_factor_observations)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'source' not in columns:
        cursor.execute("ALTER TABLE pit_factor_observations ADD COLUMN source TEXT")
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pit_factor_observations (
            factor_code TEXT,
            symbol TEXT,
            pub_date TEXT,
            obs_date TEXT,
            raw_value REAL,
            source_confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT '',
            PRIMARY KEY (factor_code, symbol, pub_date, obs_date)
        )
    """)
    conn.commit()
    conn.close()


def save_to_db(factor_code, symbol, pub_date, obs_date, raw_value, source_confidence=1.0, source=''):
    """
    带重试的数据库写入
    factor_code: 因子代码（如 JM_POS_OI）
    symbol: 品种代码（如 JM）
    pub_date: 发布日期（脚本运行日）
    obs_date: 观测日期（数据实际日期）
    raw_value: 数值（必须为float/int）
    source_confidence: 置信度 1.0=L1 0.9=L2 0.8=L3 0.5=L4回补 0.6=L4手动
    source: 数据来源描述（如 'akshare' '海关总署' 'Mysteel(年费)'）
    """
    for attempt in range(3):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.execute("""
                INSERT OR REPLACE INTO pit_factor_observations
                (factor_code, symbol, pub_date, obs_date, raw_value, source_confidence, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (factor_code, symbol, str(pub_date), str(obs_date), float(raw_value), source_confidence, source))
            conn.commit()
            conn.close()
            print(f"[DB] 写入成功: {factor_code} = {raw_value}")
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 2:
                print(f"[DB] 锁定，重试 {attempt+1}/3...")
                time.sleep(2)
            else:
                raise
    return False


def get_latest_value(factor_code, symbol, before_date=None):
    """
    获取因子最新值（用于L4兜底）
    before_date: 只取此日期之前的数据
    返回: float 或 None（兼容旧调用）
    """
    result = _get_latest_record(factor_code, symbol, before_date)
    return result[0] if result else None


def _get_latest_record(factor_code, symbol, before_date=None):
    """
    获取因子最新完整记录（用于L4兜底保留原始obs_date）
    返回: (raw_value, obs_date, source, source_confidence) 或 None
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if before_date:
            cursor.execute("""
                SELECT raw_value, obs_date, source, source_confidence
                FROM pit_factor_observations
                WHERE factor_code=? AND symbol=? AND obs_date<?
                ORDER BY obs_date DESC LIMIT 1
            """, (factor_code, symbol, str(before_date)))
        else:
            cursor.execute("""
                SELECT raw_value, obs_date, source, source_confidence
                FROM pit_factor_observations
                WHERE factor_code=? AND symbol=?
                ORDER BY obs_date DESC LIMIT 1
            """, (factor_code, symbol))
        row = cursor.fetchone()
        conn.close()
        if row:
            return (float(row[0]), row[1], row[2] or '', float(row[3]))
    except Exception as e:
        print(f"[DB] _get_latest_record失败: {e}")
    return None


def save_l4_fallback(factor_code, symbol, pub_date, today_obs_date, 
                      before_date=None, extra_msg=''):
    """
    L4兜底写入：保留原始obs_date，不以today_obs_date覆盖
    用于AKShare失败时回补历史数据
    返回: bool 是否写入成功
    """
    record = _get_latest_record(factor_code, symbol, before_date)
    if record is None:
        print(f"[L4] {factor_code} 无历史值可回补，跳过{extra_msg}")
        return False
    raw_value, orig_obs_date, orig_source, orig_conf = record
    if orig_obs_date == today_obs_date:
        # 今日已有数据，无需回补
        return False
    save_to_db(factor_code, symbol, str(pub_date), orig_obs_date,
                raw_value, source_confidence=0.5,
                source=f"L4回补({orig_source})")
    print(f"[L4] {factor_code}={raw_value} obs={orig_obs_date} (原始数据){extra_msg}")
    return True


def get_pit_dates(freq="日频"):
    """
    统一的PIT日期处理
    freq: "日频" / "周频" / "月频"
    返回: (pub_date, obs_date)
      - 工作日: 返回当天
      - 周六: 回退到周五
      - 周日/周一: 回退到上周五（周一=节假日后首个交易日之后的第一个非交易日）
    支持 BACKFILL_DATE 环境变量: 设置后强制使用该日期作为 obs_date（用于历史补采）
    """
    import datetime
    import os

    # 补采模式: BACKFILL_DATE 环境变量优先
    bf_date = os.environ.get("BACKFILL_DATE", "")
    if bf_date:
        try:
            obs_date = datetime.date.fromisoformat(bf_date)
            pub_date = obs_date
            return pub_date, obs_date
        except ValueError:
            pass  # 无效日期，降级到正常逻辑

    today = datetime.date.today()
    dow = today.weekday()

    # 周六(5)回退到周五，周日(6)/周一(0)回退到上周五
    # 周一=0: 上周五 obs_date（因为周五夜盘后到周一开盘之间无新数据）
    if dow == 6:
        obs_date = today - datetime.timedelta(days=2)   # 周日→周五
    elif dow == 5:
        obs_date = today - datetime.timedelta(days=1)   # 周六→周五
    elif dow == 0:
        obs_date = today - datetime.timedelta(days=3)   # 周一→上周五
    else:
        obs_date = today

    pub_date = today
    return pub_date, obs_date
