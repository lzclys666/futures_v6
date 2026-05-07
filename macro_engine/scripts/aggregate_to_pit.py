#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aggregate_to_pit.py

ETL 聚合脚本：将 JM/RU/RB/ZN/NI 的派生表（spread/hold_volume/ohlcv）
数据转换为 PIT 观测记录并写入 pit_factor_observations 表。

派生因子映射：
  spread 表    → {SYM}_SPD_01, {SYM}_SPD_03, {SYM}_SPD_05
  hold_volume  → {SYM}_POS_OI (持仓量汇总), {SYM}_POS_CHANGE (持仓变化汇总)
  ohlcv        → {SYM}_FUT_CLOSE (收盘价)

当前状态: ✅ 正常
"""

import sqlite3
import logging
import os
from datetime import datetime

# ── 配置 ──────────────────────────────────────────────────────────────────────
DB_PATH = r"D:\futures_v6\macro_engine\pit_data.db"
SYMBOLS = ["JM", "RU", "RB", "ZN", "NI"]
SOURCE = "aggregated"
CONFIDENCE = 0.85

# ── 日志 ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def get_spread_factor_names(sym):
    return f"{sym}_SPD_01", f"{sym}_SPD_03", f"{sym}_SPD_05"


def get_hold_factor_names(sym):
    return f"{sym}_POS_OI", f"{sym}_POS_CHANGE"


def get_ohlcv_factor_name(sym):
    return f"{sym}_FUT_CLOSE"


def process_spread(conn, sym) -> int:
    """从 spread 表写入 3 个价差因子，每个 obs_date 取最新一条记录。"""
    table = f"{sym.lower()}_futures_spread"
    written = 0

    try:
        cur = conn.cursor()
        # 探测可用列
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]

        # 确定 spread 列（可能只有 spread_01，或只有 spread_01/03，或全有）
        spread_cols = [c for c in cols if c.startswith("spread_")]
        if not spread_cols:
            log.warning(f"[{sym}] spread: 无 spread 列，跳过")
            return 0

        factor_map = {
            "spread_01": get_spread_factor_names(sym)[0],
            "spread_03": get_spread_factor_names(sym)[1],
            "spread_05": get_spread_factor_names(sym)[2],
        }

        for sc in spread_cols:
            fc = factor_map.get(sc)
            if fc is None:
                continue

            # 每个 obs_date 取 pub_date 最新的一条
            sql = f"""
                SELECT pub_date, obs_date, {sc}
                FROM {table}
                WHERE {sc} IS NOT NULL
                  AND obs_date = (
                      SELECT MAX(obs_date) FROM {table}
                      WHERE pub_date = {table}.pub_date
                        AND obs_date = {table}.obs_date
                  )
                ORDER BY obs_date DESC, pub_date DESC
            """
            # 改用窗口函数更可靠
            sql = f"""
                WITH ranked AS (
                    SELECT pub_date, obs_date, {sc},
                           ROW_NUMBER() OVER (
                               PARTITION BY obs_date
                               ORDER BY pub_date DESC
                           ) AS rn
                    FROM {table}
                    WHERE {sc} IS NOT NULL
                )
                SELECT pub_date, obs_date, {sc}
                FROM ranked
                WHERE rn = 1
            """

            cur.execute(sql)
            rows = cur.fetchall()

            stmt = """
                INSERT OR REPLACE INTO pit_factor_observations
                (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            for pub_date, obs_date, raw_val in rows:
                if raw_val is None:
                    continue
                # PIT 合规：跳过 obs_date == pub_date 的记录
                if obs_date == pub_date:
                    log.warning(f"[{sym}] spread {fc}: 跳过 obs_date=pub_date={obs_date} (PIT违规)")
                    continue
                cur.execute(stmt, (fc, sym, pub_date, obs_date, float(raw_val), SOURCE, CONFIDENCE))
                written += 1

        conn.commit()
        log.info(f"[{sym}] spread: {written} rows written")

    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            log.warning(f"[{sym}] spread: 表 {table} 不存在，跳过")
        else:
            log.error(f"[{sym}] spread: {e}")
    except Exception as e:
        log.error(f"[{sym}] spread: {e}")

    return written


def process_hold_volume(conn, sym) -> int:
    """从 hold_volume 表写入持仓量(OI)和持仓变化因子，按 obs_date 分组汇总。"""
    table = f"{sym.lower()}_futures_hold_volume"
    written = 0

    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]

        has_hold_vol = "hold_volume" in cols
        has_hold_change = "hold_change" in cols

        if not has_hold_vol and not has_hold_change:
            log.warning(f"[{sym}] hold_volume: 无 hold_volume/hold_change 列，跳过")
            return 0

        # 按 obs_date 聚合：hold_volume 求和, hold_change 求和
        # 每个 obs_date 取最新 pub_date 的聚合值
        oi_factor = get_hold_factor_names(sym)[0]
        chg_factor = get_hold_factor_names(sym)[1]

        if has_hold_vol:
            sql = f"""
                WITH daily AS (
                    SELECT obs_date, pub_date,
                           SUM(hold_volume) AS total_oi
                    FROM {table}
                    WHERE hold_volume IS NOT NULL
                    GROUP BY obs_date, pub_date
                ),
                ranked AS (
                    SELECT obs_date, total_oi,
                           ROW_NUMBER() OVER (
                               PARTITION BY obs_date
                               ORDER BY pub_date DESC
                           ) AS rn
                    FROM daily
                )
                SELECT obs_date, total_oi
                FROM ranked
                WHERE rn = 1
            """
            cur.execute(sql)
            rows = cur.fetchall()
            stmt = """
                INSERT OR REPLACE INTO pit_factor_observations
                (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            # 拿不到 pub_date，换一种写法
            sql2 = f"""
                SELECT obs_date, pub_date, SUM(hold_volume) AS total_oi
                FROM {table}
                WHERE hold_volume IS NOT NULL
                GROUP BY obs_date
                ORDER BY obs_date, pub_date DESC
            """
            cur.execute(sql2)
            raw = cur.fetchall()
            # 按 obs_date 合并，pub_date 取最新的
            obs_data = {}
            for obs_date, pub_date, total_oi in raw:
                if obs_date not in obs_data:
                    obs_data[obs_date] = (pub_date, total_oi)

            stmt = """
                INSERT OR REPLACE INTO pit_factor_observations
                (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            for obs_date, (pub_date, total_oi) in obs_data.items():
                # PIT 合规：跳过 obs_date == pub_date 的记录
                if obs_date == pub_date:
                    log.warning(f"[{sym}] hold_volume {oi_factor}: 跳过 obs_date=pub_date={obs_date} (PIT违规)")
                    continue
                cur.execute(stmt, (oi_factor, sym, pub_date, obs_date, float(total_oi), SOURCE, CONFIDENCE))
                written += 1

        if has_hold_change:
            sql = f"""
                SELECT obs_date, pub_date, SUM(hold_change) AS total_change
                FROM {table}
                WHERE hold_change IS NOT NULL
                GROUP BY obs_date
                ORDER BY obs_date, pub_date DESC
            """
            cur.execute(sql)
            raw = cur.fetchall()
            obs_data = {}
            for obs_date, pub_date, total_change in raw:
                if obs_date not in obs_data:
                    obs_data[obs_date] = (pub_date, total_change)

            stmt = """
                INSERT OR REPLACE INTO pit_factor_observations
                (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            for obs_date, (pub_date, total_change) in obs_data.items():
                # PIT 合规：跳过 obs_date == pub_date 的记录
                if obs_date == pub_date:
                    log.warning(f"[{sym}] hold_volume {chg_factor}: 跳过 obs_date=pub_date={obs_date} (PIT违规)")
                    continue
                cur.execute(stmt, (chg_factor, sym, pub_date, obs_date, float(total_change), SOURCE, CONFIDENCE))
                written += 1

        conn.commit()
        log.info(f"[{sym}] hold_volume: {written} rows written")

    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            log.warning(f"[{sym}] hold_volume: 表 {table} 不存在，跳过")
        else:
            log.error(f"[{sym}] hold_volume: {e}")
    except Exception as e:
        log.error(f"[{sym}] hold_volume: {e}")

    return written


def process_ohlcv(conn, sym) -> int:
    """从 ohlcv 表写入收盘价因子，每个 obs_date 取持仓量加权平均收盘价。"""
    table = f"{sym.lower()}_futures_ohlcv"
    written = 0

    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]

        has_close = "close" in cols
        has_hold = "hold" in cols  # 持仓量字段

        if not has_close:
            log.warning(f"[{sym}] ohlcv: 无 close 列，跳过")
            return 0

        factor = get_ohlcv_factor_name(sym)

        if has_hold:
            # 持仓量加权平均收盘价
            sql = f"""
                SELECT obs_date, pub_date,
                       SUM(close * hold) / SUM(hold) AS wavg_close
                FROM {table}
                WHERE close IS NOT NULL AND hold IS NOT NULL AND hold > 0
                GROUP BY obs_date, pub_date
                ORDER BY obs_date, pub_date DESC
            """
            cur.execute(sql)
            raw = cur.fetchall()
            obs_data = {}
            for obs_date, pub_date, wavg_close in raw:
                if obs_date not in obs_data:
                    obs_data[obs_date] = (pub_date, wavg_close)
        else:
            # 简单平均收盘价
            sql = f"""
                SELECT obs_date, pub_date, AVG(close) AS avg_close
                FROM {table}
                WHERE close IS NOT NULL
                GROUP BY obs_date, pub_date
                ORDER BY obs_date, pub_date DESC
            """
            cur.execute(sql)
            raw = cur.fetchall()
            obs_data = {}
            for obs_date, pub_date, avg_close in raw:
                if obs_date not in obs_data:
                    obs_data[obs_date] = (pub_date, avg_close)

        stmt = """
            INSERT OR REPLACE INTO pit_factor_observations
            (factor_code, symbol, pub_date, obs_date, raw_value, source, source_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        for obs_date, (pub_date, close_val) in obs_data.items():
            # PIT 合规：跳过 obs_date == pub_date 的记录
            if obs_date == pub_date:
                log.warning(f"[{sym}] ohlcv {factor}: 跳过 obs_date=pub_date={obs_date} (PIT违规)")
                continue
            cur.execute(stmt, (factor, sym, pub_date, obs_date, float(close_val), SOURCE, CONFIDENCE))
            written += 1

        conn.commit()
        log.info(f"[{sym}] ohlcv: {written} rows written")

    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            log.warning(f"[{sym}] ohlcv: 表 {table} 不存在，跳过")
        else:
            log.error(f"[{sym}] ohlcv: {e}")
    except Exception as e:
        log.error(f"[{sym}] ohlcv: {e}")

    return written


def main():
    t0 = datetime.now()
    log.info(f"=== ETL 聚合开始 | {t0.strftime('%Y-%m-%d %H:%M:%S')} ===")

    if not os.path.exists(DB_PATH):
        log.error(f"数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    # 运行前统计
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pit_factor_observations")
    total_before = cur.fetchone()[0]

    symbol_stats = {}
    for sym in SYMBOLS:
        log.info(f"--- 处理 {sym} ---")
        n1 = process_spread(conn, sym)
        n2 = process_hold_volume(conn, sym)
        n3 = process_ohlcv(conn, sym)
        symbol_stats[sym] = {"spread": n1, "hold_volume": n2, "ohlcv": n3}

    conn.commit()

    # 运行后统计
    cur.execute("SELECT COUNT(*) FROM pit_factor_observations")
    total_after = cur.fetchone()[0]

    log.info("=" * 50)
    log.info("=== ETL 聚合完成 ===")
    log.info(f"总耗时: {(datetime.now() - t0).total_seconds():.1f}s")
    log.info("")
    log.info("各品种写入统计:")
    for sym, stats in symbol_stats.items():
        total_sym = sum(stats.values())
        log.info(f"  {sym}: spread={stats['spread']}, hold_volume={stats['hold_volume']}, ohlcv={stats['ohlcv']}  →  合计 {total_sym} 条")

    log.info("")
    log.info(f"PIT 表总变化: {total_before} → {total_after} (+{total_after - total_before})")

    conn.close()


if __name__ == "__main__":
    main()
