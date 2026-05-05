"""
crawlers/common/db_utils.py
所有爬虫共享的数据库工具函数
"""

import sqlite3
import os
import time
import errno

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
    带重试的数据库写入（保护高置信度数据）
    factor_code: 因子代码（如 JM_POS_OI）
    symbol: 品种代码（如 JM）
    pub_date: 发布日期（脚本运行日）
    obs_date: 观测日期（数据实际日期）
    raw_value: 数值（必须为float/int）
    source_confidence: 置信度 1.0=L1 0.9=L2 0.8=L3 0.5=L4回补 0.6=L4手动
    source: 数据来源描述（如 'akshare' '海关总署' 'Mysteel(年费)'）
    返回: True 写入成功, False 跳过写入（已有更高置信度记录）
    """
    # 豁免逻辑：source_confidence=0.0 时跳过置信度保护，直接写入
    if source_confidence == 0.0:
        print(f"[豁免] source_confidence=0.0，跳过置信度保护，直接写入")
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            # raw_value 为 None 时直接写 NULL，不做 float() 转换
            rv = None if raw_value is None else float(raw_value)
            conn.execute("""
                INSERT OR REPLACE INTO pit_factor_observations
                (factor_code, symbol, pub_date, obs_date, raw_value, source_confidence, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (factor_code, symbol, str(pub_date), str(obs_date), rv, source_confidence, source))
            conn.commit()
            conn.close()
            print(f"[DB] 豁免写入: {factor_code} = {raw_value}")
            return True
        except Exception as e:
            print(f"[DB] 豁免写入失败: {e}")
            return False
    return _save_with_retry(factor_code, symbol, pub_date, obs_date, raw_value, source_confidence, source)


def _save_with_retry(factor_code, symbol, pub_date, obs_date, raw_value, source_confidence, source):
    """
    带区分错误类型的重试逻辑
    - sqlite3.OperationalError("locked"): 重试3次
    - sqlite3.OperationalError("not locked") 或其他 DatabaseError: 重试2次
    - PermissionError / OSError(WinError 112/5): 不重试，直接返回 False
    """
    # 置信度保护查询
    def _do_write():
        conn = sqlite3.connect(DB_PATH, timeout=10)
        existing = conn.execute("""
            SELECT source_confidence FROM pit_factor_observations
            WHERE factor_code=? AND symbol=? AND pub_date=? AND obs_date=?
        """, (factor_code, symbol, str(pub_date), str(obs_date))).fetchone()
        if existing is not None:
            if float(existing[0]) >= float(source_confidence):
                conn.close()
                print(f"[DB] 跳过（已有更高置信度 {existing[0]:.1f} >= {source_confidence:.1f}）: {factor_code}")
                return False
        conn.execute("""
            INSERT OR REPLACE INTO pit_factor_observations
            (factor_code, symbol, pub_date, obs_date, raw_value, source_confidence, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (factor_code, symbol, str(pub_date), str(obs_date), float(raw_value), source_confidence, source))
        conn.commit()
        conn.close()
        print(f"[DB] 写入成功: {factor_code} = {raw_value}")
        return True

    attempt = 0
    max_retries_locked = 3
    max_retries_other = 2

    while True:
        try:
            result = _do_write()
            return result
        except sqlite3.OperationalError as e:
            err_str = str(e).lower()
            if "locked" in err_str:
                # 已有逻辑：locked 最多重试3次
                if attempt < max_retries_locked - 1:
                    attempt += 1
                    print(f"[DB] OperationalError(locked)，重试 {attempt}/{max_retries_locked}...")
                    time.sleep(2)
                    continue
                else:
                    print(f"[DB] OperationalError(locked) 重试耗尽: {e}")
                    return False
            else:
                # "not locked" 或其他操作错误，重试2次
                if attempt < max_retries_other - 1:
                    attempt += 1
                    print(f"[DB] OperationalError(not locked)，重试 {attempt}/{max_retries_other}...")
                    time.sleep(2)
                    continue
                else:
                    print(f"[DB] OperationalError(not locked) 重试耗尽: {e}")
                    return False
        except sqlite3.DatabaseError as e:
            # DatabaseError（非 OperationalError 子类），重试2次
            if attempt < max_retries_other - 1:
                attempt += 1
                print(f"[DB] DatabaseError，重试 {attempt}/{max_retries_other}...")
                time.sleep(2)
                continue
            else:
                print(f"[DB] DatabaseError 重试耗尽: {e}")
                return False
        except PermissionError as e:
            print(f"[DB] PermissionError，不重试: {e}")
            return False
        except OSError as e:
            # WinError 112 = 磁盘满，WinError 5 = 权限拒绝，均不重试
            if e.winerror in (112, 5):
                print(f"[DB] OSError(WinError {e.winerror})，不重试: {e}")
                return False
            # 其他 OSError 当作 DatabaseError 处理
            if attempt < max_retries_other - 1:
                attempt += 1
                print(f"[DB] OSError，重试 {attempt}/{max_retries_other}...")
                time.sleep(2)
                continue
            else:
                print(f"[DB] OSError 重试耗尽: {e}")
                return False
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
                WHERE factor_code=? AND symbol=? AND raw_value IS NOT NULL
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
