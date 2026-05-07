# -*- coding: utf-8 -*-
"""
ReconciliationEngine - 订单对账引擎核心

提供订单↔成交↔持仓↔账户的四向对账能力，确保交易链路端到端可审计、可验证。

数据库文件：D:\futures_v6\macro_engine\recon.db
五张表：recon_orders / recon_trades / recon_positions / recon_discrepancies / recon_daily_summary

使用示例：
    engine = get_reconciliation_engine()
    order_uuid = engine.record_order({...})
    trade_uuid = engine.record_trade({...})
    result = engine.check_order_trade_match(order_uuid)
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import pytz

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
try:
    from macro_engine.config.paths import MACRO_ENGINE
except ImportError:
    # Fallback: 从 services 目录向上两级
    import os
    MACRO_ENGINE = Path(__file__).resolve().parent.parent / "macro_engine"

RECON_DB_PATH = MACRO_ENGINE / "recon.db"

# ---------------------------------------------------------------------------
# CTP 订单状态映射
# ---------------------------------------------------------------------------

CTP_STATUS_MAP = {
    0: "PENDING",     # 报单中
    1: "PENDING",     # 已报
    2: "PARTIAL",     # 部成
    3: "FILLED",      # 已成
    4: "PENDING",     # 未成
    5: "CANCELLED",   # 已撤
    6: "PARTIAL",     # 部撤（取 PARTIAL，附带 CANCELLED 标记）
    7: "REJECTED",    # 废单
}


def map_ctp_status(ctp_status: int) -> str:
    """将 CTP 订单状态码映射为内部状态字符串。"""
    return CTP_STATUS_MAP.get(ctp_status, "UNKNOWN")


# ---------------------------------------------------------------------------
# 时间戳工具函数
# ---------------------------------------------------------------------------

def now_cst() -> str:
    """返回当前北京时间 ISO 8601 格式（带 +08:00 时区后缀）。"""
    return datetime.now(pytz.timezone("Asia/Shanghai")).strftime(
        "%Y-%m-%dT%H:%M:%S+08:00"
    )


def parse_cst(ts: str) -> datetime:
    """解析北京时间 ISO 8601 字符串为 datetime 对象。"""
    # 处理 "+08:00" 和 "CST" 等非标准后缀
    ts = ts.replace(" CST", "+08:00").replace(" cst", "+08:00")
    return datetime.fromisoformat(ts)


# ---------------------------------------------------------------------------
# 建表 SQL（严格按 D5 方案）
# ---------------------------------------------------------------------------

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS recon_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_uuid TEXT UNIQUE NOT NULL,
    client_order_id TEXT,
    vt_orderid TEXT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,
    offset TEXT NOT NULL,
    price REAL NOT NULL,
    volume INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    rejection_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS recon_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_uuid TEXT UNIQUE NOT NULL,
    ref_order_uuid TEXT NOT NULL,
    vt_tradeid TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,
    offset TEXT NOT NULL,
    price REAL NOT NULL,
    volume INTEGER NOT NULL,
    trade_time TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (ref_order_uuid) REFERENCES recon_orders(order_uuid)
);

CREATE TABLE IF NOT EXISTS recon_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,
    today_volume INTEGER NOT NULL DEFAULT 0,
    yd_volume INTEGER NOT NULL DEFAULT 0,
    total_volume INTEGER NOT NULL DEFAULT 0,
    avg_price REAL NOT NULL DEFAULT 0.0,
    last_price REAL NOT NULL DEFAULT 0.0,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    market_value REAL NOT NULL DEFAULT 0.0,
    settlement_price REAL,
    recorded_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'calculated'
);

CREATE TABLE IF NOT EXISTS recon_discrepancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discrepancy_uuid TEXT UNIQUE NOT NULL,
    ref_order_uuid TEXT,
    discrepancy_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'WARNING',
    description TEXT NOT NULL,
    expected_value TEXT,
    actual_value TEXT,
    resolved INTEGER DEFAULT 0,
    resolved_reason TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recon_daily_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT UNIQUE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    total_volume INTEGER DEFAULT 0,
    total_turnover REAL DEFAULT 0.0,
    realized_pnl REAL DEFAULT 0.0,
    starting_equity REAL DEFAULT 0.0,
    cash_flow REAL DEFAULT 0.0,
    commission REAL DEFAULT 0.0,
    ending_equity REAL DEFAULT 0.0,
    frozen_margin REAL DEFAULT 0.0,
    unrealized_pnl REAL DEFAULT 0.0,
    alerts_count INTEGER DEFAULT 0,
    discrepancies_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'OK',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recon_position_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_uuid TEXT UNIQUE NOT NULL,
    trade_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,
    today_volume INTEGER NOT NULL DEFAULT 0,
    yd_volume INTEGER NOT NULL DEFAULT 0,
    total_volume INTEGER NOT NULL DEFAULT 0,
    avg_price REAL NOT NULL DEFAULT 0.0,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    market_value REAL NOT NULL DEFAULT 0.0,
    frozen_margin REAL NOT NULL DEFAULT 0.0,
    snapshot_type TEXT NOT NULL DEFAULT 'DAILY_SNAPSHOT',
    recorded_at TEXT NOT NULL,
    UNIQUE(trade_date, symbol, exchange, direction)
);
"""

_CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_orders_uuid ON recon_orders(order_uuid);",
    "CREATE INDEX IF NOT EXISTS idx_orders_client ON recon_orders(client_order_id);",
    "CREATE INDEX IF NOT EXISTS idx_orders_vt ON recon_orders(vt_orderid);",
    "CREATE INDEX IF NOT EXISTS idx_orders_symbol ON recon_orders(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_orders_status ON recon_orders(status);",
    "CREATE INDEX IF NOT EXISTS idx_orders_created ON recon_orders(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_trades_uuid ON recon_trades(trade_uuid);",
    "CREATE INDEX IF NOT EXISTS idx_trades_order ON recon_trades(ref_order_uuid);",
    "CREATE INDEX IF NOT EXISTS idx_trades_vt ON recon_trades(vt_tradeid);",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_pos_symbol_dir ON recon_positions(symbol, exchange, direction);",
    "CREATE INDEX IF NOT EXISTS idx_pos_recorded ON recon_positions(recorded_at);",
    "CREATE INDEX IF NOT EXISTS idx_disc_type ON recon_discrepancies(discrepancy_type);",
    "CREATE INDEX IF NOT EXISTS idx_disc_resolved ON recon_discrepancies(resolved);",
    "CREATE INDEX IF NOT EXISTS idx_disc_created ON recon_discrepancies(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_summary_date ON recon_daily_summary(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_recorded ON recon_position_snapshots(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_symbol ON recon_position_snapshots(symbol, exchange, direction);",
]


# ---------------------------------------------------------------------------
# ReconciliationEngine
# ---------------------------------------------------------------------------

class ReconciliationEngine:
    """
    订单对账引擎核心类。

    管理订单、成交、持仓、差异记录的持久化和对账检查。
    数据库路径默认为 D:\\futures_v6\\macro_engine\\recon.db
    使用 check_same_thread=False 以支持多线程访问。
    所有写入操作受线程锁保护。
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = Path(db_path) if db_path else RECON_DB_PATH
        self._lock = threading.RLock()  # reentrant, safe for nested _lock calls
        self._init_db()

    # ---- 数据库初始化 ---------------------------------------------------

    def _init_db(self) -> None:
        """初始化数据库和所有表（幂等操作）。"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_CREATE_TABLES_SQL)
            for idx_sql in _CREATE_INDEXES_SQL:
                conn.execute(idx_sql)
            conn.commit()

    def _connect(self):
        """
        创建数据库连接并返回上下文管理器。

        用法：with self._connect() as conn: ...
        退出 with 块时自动 commit（成功）或 rollback（异常），并关闭连接。
        解决原 _connect() 连接泄漏问题：sqlite3.Connection.__exit__
        只做 commit/rollback，不关闭连接。
        """
        class _ConnCtx:
            def __init__(self, db_path_str):
                self._db_path_str = db_path_str
                self.conn = None

            def __enter__(self):
                self.conn = sqlite3.connect(self._db_path_str, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                # 启用外键约束（SQLite 默认不启用）
                self.conn.execute("PRAGMA foreign_keys = ON")
                return self.conn

            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.conn is None:
                    return False
                try:
                    if exc_type is None:
                        self.conn.commit()
                    else:
                        self.conn.rollback()
                finally:
                    self.conn.close()
                    self.conn = None
                return False

        return _ConnCtx(str(self._db_path))

    # ---- 写入 API ------------------------------------------------------

    def record_order(self, order_data: dict) -> str:
        """
        将一笔订单写入 recon_orders 表。

        Args:
            order_data: 至少包含以下键的字典
                symbol, exchange, direction, offset, price, volume
                可选键：client_order_id, vt_orderid, status, source

        Returns:
            order_uuid（字符串）
        """
        order_uuid = str(uuid.uuid4())
        now = now_cst()

        with self._lock:
            # 重复订单检测：5分钟窗口内相同 client_order_id
            client_order_id = order_data.get("client_order_id")
            if client_order_id:
                is_dup = self._check_duplicate_order_internal(
                    client_order_id, now
                )
                # 仅记录告警，不阻止写入（可能为合法重试）

            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO recon_orders
                    (order_uuid, client_order_id, vt_orderid, symbol, exchange,
                     direction, offset, price, volume, status, created_at, updated_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_uuid,
                        order_data.get("client_order_id"),
                        order_data.get("vt_orderid"),
                        order_data.get("symbol", ""),
                        order_data.get("exchange", ""),
                        order_data.get("direction", ""),
                        order_data.get("offset", ""),
                        float(order_data.get("price", 0.0)),
                        int(order_data.get("volume", 0)),
                        order_data.get("status", "PENDING"),
                        order_data.get("created_at", now),
                        now,
                        order_data.get("source", "unknown"),
                    ),
                )
                conn.commit()

        return order_uuid

    def record_trade(self, trade_data: dict) -> str:
        """
        将一笔成交写入 recon_trades 表。

        Args:
            trade_data: 至少包含以下键的字典
                ref_order_uuid, vt_tradeid, symbol, exchange,
                direction, offset, price, volume, trade_time
                可选键：source

        Returns:
            trade_uuid（字符串）

        Raises:
            ValueError: ref_order_uuid 为空或找不到对应订单
        """
        ref_order_uuid = trade_data.get("ref_order_uuid", "")
        if not ref_order_uuid:
            raise ValueError(
                "record_trade() ref_order_uuid 不能为空，"
                "请确保传入有效的关联订单 UUID"
            )

        trade_uuid = str(uuid.uuid4())
        now = now_cst()

        with self._lock:
            with self._connect() as conn:
                # 验证关联订单存在
                order_exists = conn.execute(
                    "SELECT 1 FROM recon_orders WHERE order_uuid = ?",
                    (ref_order_uuid,),
                ).fetchone()
                if not order_exists:
                    raise ValueError(
                        f"record_trade() 关联订单 {ref_order_uuid} 不存在，"
                        f"请先通过 record_order() 创建订单"
                    )

                conn.execute(
                    """
                    INSERT INTO recon_trades
                    (trade_uuid, ref_order_uuid, vt_tradeid, symbol, exchange,
                     direction, offset, price, volume, trade_time, created_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade_uuid,
                        ref_order_uuid,
                        trade_data.get("vt_tradeid"),
                        trade_data.get("symbol", ""),
                        trade_data.get("exchange", ""),
                        trade_data.get("direction", ""),
                        trade_data.get("offset", ""),
                        float(trade_data.get("price", 0.0)),
                        int(trade_data.get("volume", 0)),
                        trade_data.get("trade_time", now),
                        now,
                        trade_data.get("source", "unknown"),
                    ),
                )
                conn.commit()

        return trade_uuid

    def update_order_status(self, order_uuid: str, status: str,
                             rejection_reason: str = None) -> bool:
        """
        更新订单状态。

        Args:
            order_uuid: 订单 UUID
            status: 新状态（PENDING / PARTIAL / FILLED / CANCELLED / REJECTED）
            rejection_reason: 废单原因（仅 REJECTED 时需要）

        Returns:
            True = 更新成功，False = 订单不存在或状态无效
        """
        valid_statuses = {"PENDING", "PARTIAL", "FILLED", "CANCELLED", "REJECTED"}
        if status not in valid_statuses:
            return False

        now = now_cst()
        with self._lock:
            with self._connect() as conn:
                rows_affected = conn.execute(
                    """
                    UPDATE recon_orders
                    SET status = ?, updated_at = ?,
                        rejection_reason = COALESCE(?, rejection_reason)
                    WHERE order_uuid = ?
                    """,
                    (status, now, rejection_reason, order_uuid),
                ).rowcount
                conn.commit()
                return rows_affected > 0

    def get_discrepancies(
        self, unresolved_only: bool = False, limit: int = 50
    ) -> dict:
        """
        查询差异记录列表。

        Args:
            unresolved_only: 只返回未解决的差异
            limit: 最大返回条数

        Returns:
            {"items": [...], "total": int}
        """
        with self._lock:
            with self._connect() as conn:
                if unresolved_only:
                    rows = conn.execute(
                        """
                        SELECT * FROM recon_discrepancies
                        WHERE resolved = 0
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()
                    total = conn.execute(
                        "SELECT COUNT(*) FROM recon_discrepancies WHERE resolved = 0"
                    ).fetchone()[0]
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM recon_discrepancies
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()
                    total = conn.execute(
                        "SELECT COUNT(*) FROM recon_discrepancies"
                    ).fetchone()[0]

                items = []
                for row in rows:
                    d = dict(row)
                    items.append({
                        "id": d["id"],
                        "discrepancy_uuid": d["discrepancy_uuid"],
                        "ref_order_uuid": d["ref_order_uuid"],
                        "discrepancy_type": d["discrepancy_type"],
                        "severity": d["severity"],
                        "description": d["description"],
                        "expected_value": d["expected_value"],
                        "actual_value": d["actual_value"],
                        "resolved": bool(d["resolved"]),
                        "resolved_reason": d["resolved_reason"],
                        "resolved_at": d["resolved_at"],
                        "created_at": d["created_at"],
                    })

                return {"items": items, "total": total}

    def resolve_discrepancy(self, disc_id: int, reason: str) -> bool:
        """
        标记差异为已解决。

        Args:
            disc_id: recon_discrepancies 表的 INTEGER 主键
            reason: 解决原因

        Returns:
            True = 成功，False = 记录不存在
        """
        now = now_cst()
        with self._lock:
            with self._connect() as conn:
                rows_affected = conn.execute(
                    """
                    UPDATE recon_discrepancies
                    SET resolved = 1, resolved_reason = ?, resolved_at = ?
                    WHERE id = ?
                    """,
                    (reason, now, disc_id),
                ).rowcount
                conn.commit()
                return rows_affected > 0

    def record_position(self, position_data: dict) -> None:
        """
        写入或更新 recon_positions 表。

        Args:
            position_data: 至少包含 symbol, exchange, direction
                可选键：today_volume, yd_volume, total_volume,
                        avg_price, last_price, unrealized_pnl,
                        market_value, settlement_price, source
        """
        now = now_cst()
        today_vol = int(position_data.get("today_volume", 0))
        yd_vol = int(position_data.get("yd_volume", 0))
        total_vol = int(position_data.get("total_volume", today_vol + yd_vol))

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO recon_positions
                    (symbol, exchange, direction, today_volume, yd_volume,
                     total_volume, avg_price, last_price, unrealized_pnl,
                     market_value, settlement_price, recorded_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, exchange, direction)
                    DO UPDATE SET
                        today_volume = excluded.today_volume,
                        yd_volume    = excluded.yd_volume,
                        total_volume = excluded.total_volume,
                        avg_price    = excluded.avg_price,
                        last_price   = excluded.last_price,
                        unrealized_pnl = excluded.unrealized_pnl,
                        market_value  = excluded.market_value,
                        settlement_price = excluded.settlement_price,
                        recorded_at   = excluded.recorded_at,
                        source        = excluded.source
                    """,
                    (
                        position_data.get("symbol", ""),
                        position_data.get("exchange", ""),
                        position_data.get("direction", ""),
                        today_vol,
                        yd_vol,
                        total_vol,
                        float(position_data.get("avg_price", 0.0)),
                        float(position_data.get("last_price", 0.0)),
                        float(position_data.get("unrealized_pnl", 0.0)),
                        float(position_data.get("market_value", 0.0)),
                        position_data.get("settlement_price"),
                        now,
                        position_data.get("source", "calculated"),
                    ),
                )
                conn.commit()

    # ---- 查询辅助 ------------------------------------------------------

    def get_filled_volume(self, order_uuid: str) -> int:
        """
        查询指定订单的累计成交总量。

        规则：filled_volume 不在 recon_orders 存储，改为查询时计算。

        Args:
            order_uuid: 订单 UUID

        Returns:
            累计成交手数（整数），无成交时返回 0
        """
        with self._lock:
            with self._connect() as conn:
                return self._get_filled_volume_with_conn(conn, order_uuid)

    def _get_filled_volume_with_conn(self, conn, order_uuid: str) -> int:
        """使用共享连接查询累计成交总量（内部辅助方法）。"""
        row = conn.execute(
            "SELECT COALESCE(SUM(volume), 0) AS total "
            "FROM recon_trades WHERE ref_order_uuid = ?",
            (order_uuid,),
        ).fetchone()
        return int(row["total"]) if row else 0

    # ---- 对账检查 ------------------------------------------------------

    def check_order_trade_match(self, order_uuid: str, conn=None) -> Optional[dict]:
        """
        对账规则1：订单委托量 vs 成交总量。

        返回差异 dict，无差异时返回 None。差异类型：
          - ORDER_TRADE_MISMATCH
          - DUPLICATE_ORDER

        Args:
            order_uuid: 订单 UUID
            conn: 可选的共享数据库连接（由 reconcile_all 传入，避免嵌套创建新连接）
        """
        def _do_check(c):
            order_row = c.execute(
                "SELECT * FROM recon_orders WHERE order_uuid = ?",
                (order_uuid,),
            ).fetchone()

            if not order_row:
                return None

            order = dict(order_row)
            filled_volume = self._get_filled_volume_with_conn(c, order_uuid)
            commissioned_volume = int(order["volume"])

            # 规则1-1：成交总量 > 委托量 → CRITICAL
            if filled_volume > commissioned_volume:
                disc = {
                    "discrepancy_uuid": str(uuid.uuid4()),
                    "ref_order_uuid": order_uuid,
                    "discrepancy_type": "ORDER_TRADE_MISMATCH",
                    "severity": "CRITICAL",
                    "description": (
                        f"订单{order['symbol']}.{order['direction']}成交超出委托量："
                        f"委托{commissioned_volume}手，实际成交{filled_volume}手"
                    ),
                    "expected_value": json.dumps({"filled_volume": commissioned_volume}),
                    "actual_value": json.dumps({"filled_volume": filled_volume}),
                }
                self._emit_discrepancy_alert(disc, conn=c)
                return disc

            # 规则1-2：部分成交但状态不是 PARTIAL
            if 0 < filled_volume < commissioned_volume and order["status"] not in ("PARTIAL", "PENDING"):
                disc = {
                    "discrepancy_uuid": str(uuid.uuid4()),
                    "ref_order_uuid": order_uuid,
                    "discrepancy_type": "ORDER_TRADE_MISMATCH",
                    "severity": "WARNING",
                    "description": (
                        f"订单{order['symbol']}.{order['direction']}部分成交但状态异常："
                        f"委托{commissioned_volume}手，成交{filled_volume}手，状态{order['status']}"
                    ),
                    "expected_value": json.dumps({"filled_volume": commissioned_volume}),
                    "actual_value": json.dumps({"filled_volume": filled_volume}),
                }
                self._emit_discrepancy_alert(disc, conn=c)
                return disc

            # 规则1-3：重复 vt_tradeid 检测
            dup_trade = c.execute(
                "SELECT vt_tradeid, COUNT(*) AS cnt FROM recon_trades "
                "WHERE ref_order_uuid = ? GROUP BY vt_tradeid HAVING cnt > 1",
                (order_uuid,),
            ).fetchone()
            if dup_trade:
                disc = {
                    "discrepancy_uuid": str(uuid.uuid4()),
                    "ref_order_uuid": order_uuid,
                    "discrepancy_type": "DUPLICATE_TRADE",
                    "severity": "CRITICAL",
                    "description": f"检测到重复成交ID：{dup_trade['vt_tradeid']}",
                    "expected_value": json.dumps({"duplicate_vt_tradeid": False}),
                    "actual_value": json.dumps({"duplicate_vt_tradeid": True}),
                }
                self._emit_discrepancy_alert(disc, conn=c)
                return disc

            return None

        if conn is not None:
            # 由 reconcile_all 传入共享连接，直接使用（调用者已持有 _lock）
            return _do_check(conn)

        with self._lock:
            with self._connect() as conn:
                return _do_check(conn)

    def check_position_consistency(self, symbol: str, direction: str, conn=None) -> Optional[dict]:
        """
        对账规则2：持仓校验（今仓/昨仓分离）。

        Args:
            symbol: 品种代码（如 RU2505）
            direction: LONG / SHORT
            conn: 可选的共享数据库连接（由 reconcile_all 传入）

        返回差异 dict，无差异时返回 None。
        """
        def _do_check(c):
            row = c.execute(
                "SELECT * FROM recon_positions "
                "WHERE symbol = ? AND direction = ? "
                "ORDER BY recorded_at DESC LIMIT 1",
                (symbol, direction),
            ).fetchone()

            if not row:
                return None

            pos = dict(row)
            total = pos["total_volume"]
            today = pos["today_volume"]
            yd = pos["yd_volume"]

            # 基本一致性检查：total = today + yd
            if total != today + yd:
                disc = {
                    "discrepancy_uuid": str(uuid.uuid4()),
                    "ref_order_uuid": None,
                    "discrepancy_type": "POSITION_MISMATCH",
                    "severity": "WARNING",
                    "description": (
                        f"持仓{symbol}.{direction}今昨仓数据不一致："
                        f"今仓{today} + 昨仓{yd} ≠ 总持仓{total}"
                    ),
                    "expected_value": json.dumps({"total": today + yd}),
                    "actual_value": json.dumps({"total": total}),
                }
                self._emit_discrepancy_alert(disc, conn=c)
                return disc

            # 交叉验证：用 recon_trades 校验今仓量
            today_trades = c.execute(
                """
                SELECT COALESCE(SUM(volume), 0) AS today_bought
                FROM recon_trades
                WHERE symbol = ? AND direction = ?
                  AND created_at >= ?
                """,
                (symbol, direction, f"{now_cst()[:10]}T00:00:00+08:00"),
            ).fetchone()
            if today_trades and today != int(today_trades["today_bought"]):
                # 今仓与当日成交有差异（仅 WARNING，因为今仓可能被部分平仓）
                pass  # 信息差异暂不报警，记录即可

            return None

        if conn is not None:
            return _do_check(conn)

        with self._lock:
            with self._connect() as conn:
                return _do_check(conn)

    def check_account_equity(
        self, starting_equity: float, cash_flow: float,
        trade_date: Optional[str] = None
    ) -> Optional[dict]:
        """
        对账规则3：账户权益校验（含出入金）。

        权益公式：
            ending_equity = starting_equity + realized_pnl - commission
                           + unrealized_pnl + cash_flow

        本方法仅校验 equity 差异阈值（>100元 WARNING，>1000元 CRITICAL）。
        实际 ending_equity 由调用方传入进行对比。

        Args:
            starting_equity: 日初权益
            cash_flow: 净出入金（正为入金，负为出金）
            trade_date: 交易日期（YYYY-MM-DD），None 则使用当天

        Returns:
            差异 dict；若无足够数据计算则返回 None
        """
        if trade_date is None:
            trade_date = now_cst()[:10]

        with self._lock:
            with self._connect() as conn:
                # 从 recon_trades 汇总当日成交（添加日期过滤）
                trade_row = conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(volume * price), 0.0) AS total_turnover,
                        COUNT(*) AS trade_count
                    FROM recon_trades
                    WHERE created_at >= ? AND created_at < ?
                    """,
                    (f"{trade_date}T00:00:00+08:00", f"{trade_date}T23:59:59+08:00"),
                ).fetchone()

                # 从 recon_daily_summary 取最新一条
                summary_row = conn.execute(
                    "SELECT * FROM recon_daily_summary "
                    "ORDER BY trade_date DESC LIMIT 1"
                ).fetchone()

                if not summary_row:
                    return None

                summary = dict(summary_row)
                realized_pnl = summary.get("realized_pnl", 0.0)
                commission = summary.get("commission", 0.0)
                unrealized_pnl = summary.get("unrealized_pnl", 0.0)
                ending_equity = summary.get("ending_equity", 0.0)

                # 计算预期权益
                expected = (
                    starting_equity
                    + realized_pnl
                    - commission
                    + unrealized_pnl
                    + cash_flow
                )

                diff = abs(ending_equity - expected)
                if diff > 1000:
                    severity = "CRITICAL"
                elif diff > 100:
                    severity = "WARNING"
                else:
                    return None

                disc = {
                    "discrepancy_uuid": str(uuid.uuid4()),
                    "ref_order_uuid": None,
                    "discrepancy_type": "BALANCE_MISMATCH",
                    "severity": severity,
                    "description": (
                        f"账户权益偏差{diff:.2f}元："
                        f"期望{expected:.2f}，实际{ending_equity:.2f}"
                    ),
                    "expected_value": json.dumps(
                        {"ending_equity": expected}
                    ),
                    "actual_value": json.dumps(
                        {"ending_equity": ending_equity}
                    ),
                }
                self._emit_discrepancy_alert(disc)
                return disc

    def check_duplicate_order(
        self, client_order_id: str, created_at: str
    ) -> bool:
        """
        检测重复订单：5分钟窗口内相同 client_order_id。

        Args:
            client_order_id: 客户端订单ID
            created_at: 发单时间（ISO 8601 +08:00）

        Returns:
            True = 重复，False = 正常
        """
        if not client_order_id:
            return False

        with self._lock:
            return self._check_duplicate_order_internal(client_order_id, created_at)

    def _check_duplicate_order_internal(
        self, client_order_id: str, created_at: str
    ) -> bool:
        """
        内部重复订单检测（调用方需已持有 self._lock）。

        Args:
            client_order_id: 客户端订单ID
            created_at: 发单时间（ISO 8601 +08:00）

        Returns:
            True = 重复，False = 正常
        """
        try:
            created_dt = parse_cst(created_at)
            window_start = (created_dt - timedelta(minutes=5)).strftime(
                "%Y-%m-%dT%H:%M:%S+08:00"
            )
        except Exception:
            window_start = created_at

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT 1 FROM recon_orders
                WHERE client_order_id = ?
                  AND created_at >= ?
                  AND created_at <= ?
                LIMIT 1
                """,
                (client_order_id, window_start, created_at),
            ).fetchone()

            if existing:
                disc = {
                    "discrepancy_uuid": str(uuid.uuid4()),
                    "ref_order_uuid": None,
                    "discrepancy_type": "DUPLICATE_ORDER",
                    "severity": "WARNING",
                    "description": (
                        f"检测到重复订单 client_order_id={client_order_id}，"
                        f"5分钟窗口内已存在"
                    ),
                    "expected_value": json.dumps({"duplicate": False}),
                    "actual_value": json.dumps({"duplicate": True}),
                }
                self._emit_discrepancy_alert(disc)
                return True

            return False

    def reconcile_all(self) -> dict:
        """
        执行全量对账，返回检查统计。

        Returns:
            dict，包含 checked_orders / checked_trades / checked_positions /
                   new_discrepancies / resolved_discrepancies
        """
        stats = {
            "checked_orders": 0,
            "checked_trades": 0,
            "checked_positions": 0,
            "new_discrepancies": 0,
            "resolved_discrepancies": 0,
        }

        with self._lock:
            with self._connect() as conn:
                # 对所有未终结的订单执行 Order↔Trade 对账
                orders = conn.execute(
                    "SELECT order_uuid FROM recon_orders "
                    "WHERE status IN ('PENDING', 'PARTIAL')"
                ).fetchall()
                stats["checked_orders"] = len(orders)

                for row in orders:
                    # 传入共享连接，避免嵌套创建新连接导致快照不一致
                    disc = self.check_order_trade_match(row["order_uuid"], conn=conn)
                    if disc:
                        stats["new_discrepancies"] += 1

                # 对所有持仓执行一致性校验
                positions = conn.execute(
                    "SELECT symbol, direction FROM recon_positions"
                ).fetchall()
                stats["checked_positions"] = len(positions)

                seen = set()
                for row in positions:
                    key = (row["symbol"], row["direction"])
                    if key in seen:
                        continue
                    seen.add(key)
                    # 传入共享连接
                    disc = self.check_position_consistency(key[0], key[1], conn=conn)
                    if disc:
                        stats["new_discrepancies"] += 1

                stats["checked_trades"] = conn.execute(
                    "SELECT COUNT(*) FROM recon_trades"
                ).fetchone()[0]

                # 统计已解决的差异（上次 reconcile_all 以来被标记为 resolved 的）
                stats["resolved_discrepancies"] = conn.execute(
                    "SELECT COUNT(*) FROM recon_discrepancies WHERE resolved = 1"
                ).fetchone()[0]

        return stats

    # ---- 告警 ---------------------------------------------------------

    def _emit_discrepancy_alert(self, disc: dict, conn=None) -> None:
        """
        将差异记录写入 recon_discrepancies 表。

        注意：本方法不获取 self._lock，因为所有调用者（record_order,
        check_order_trade_match, check_position_consistency 等）已持有锁。
        通过 conn 参数可传入共享连接，避免在已持有锁时创建新连接。

        告警推送由 API 层通过 AlertManager 异步处理，
        本方法仅负责持久化，避免因 AlertManager 初始化/导入
        失败而阻塞对账核心。
        """
        def _write(c):
            c.execute(
                """
                INSERT INTO recon_discrepancies
                (discrepancy_uuid, ref_order_uuid, discrepancy_type,
                 severity, description, expected_value, actual_value,
                 created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    disc["discrepancy_uuid"],
                    disc.get("ref_order_uuid"),
                    disc["discrepancy_type"],
                    disc["severity"],
                    disc["description"],
                    disc.get("expected_value"),
                    disc.get("actual_value"),
                    now_cst(),
                ),
            )
            c.commit()

        if conn is not None:
            _write(conn)
        else:
            with self._connect() as c:
                _write(c)

    # ---- 状态 ---------------------------------------------------------

    def get_status(self) -> dict:
        """
        返回对账引擎当前状态。

        Returns:
            dict，包含：
                engine_status, last_recon_time,
                orders_count, trades_count, positions_count,
                discrepancies (unresolved/WARNING/CRITICAL)
        """
        with self._lock:
            with self._connect() as conn:
                # last_recon_time：使用 recon_daily_summary 最新记录的 created_at
                # 语义上代表最后一次日终对账的时间，而非差异产生时间
                try:
                    last_row = conn.execute(
                        "SELECT created_at FROM recon_daily_summary "
                        "ORDER BY trade_date DESC LIMIT 1"
                    ).fetchone()
                    last_recon = last_row["created_at"] if last_row else None
                except Exception:
                    last_recon = None

                orders_count = conn.execute(
                    "SELECT COUNT(*) FROM recon_orders"
                ).fetchone()[0]
                trades_count = conn.execute(
                    "SELECT COUNT(*) FROM recon_trades"
                ).fetchone()[0]
                positions_count = conn.execute(
                    "SELECT COUNT(*) FROM recon_positions"
                ).fetchone()[0]

                disc_unresolved = conn.execute(
                    "SELECT COUNT(*) FROM recon_discrepancies WHERE resolved = 0"
                ).fetchone()[0]
                disc_warning = conn.execute(
                    "SELECT COUNT(*) FROM recon_discrepancies "
                    "WHERE resolved = 0 AND severity = 'WARNING'"
                ).fetchone()[0]
                disc_critical = conn.execute(
                    "SELECT COUNT(*) FROM recon_discrepancies "
                    "WHERE resolved = 0 AND severity = 'CRITICAL'"
                ).fetchone()[0]

        return {
            "engine_status": "ok",
            "last_recon_time": last_recon,
            "orders_count": orders_count,
            "trades_count": trades_count,
            "positions_count": positions_count,
            "discrepancies": {
                "unresolved": disc_unresolved,
                "WARNING": disc_warning,
                "CRITICAL": disc_critical,
            },
        }

    def save_daily_summary(
        self, trade_date: str, summary_data: dict
    ) -> None:
        """
        写入或更新 recon_daily_summary 表。

        部分更新语义：仅更新 summary_data 中提供的字段，未提供的字段保留原值。
        created_at 保留首次创建时间，新增 updated_at 字段记录更新时间。

        Args:
            trade_date: 交易日期字符串（YYYY-MM-DD 北京时间）
            summary_data: 可包含 total_orders / total_trades /
                         total_volume / total_turnover 等字段的字典
        """
        now = now_cst()

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO recon_daily_summary
                    (trade_date, total_orders, total_trades, total_volume,
                     total_turnover, realized_pnl, starting_equity, cash_flow,
                     commission, ending_equity, frozen_margin, unrealized_pnl,
                     alerts_count, discrepancies_count, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(trade_date) DO UPDATE SET
                        total_orders         = COALESCE(excluded.total_orders, recon_daily_summary.total_orders),
                        total_trades         = COALESCE(excluded.total_trades, recon_daily_summary.total_trades),
                        total_volume         = COALESCE(excluded.total_volume, recon_daily_summary.total_volume),
                        total_turnover       = COALESCE(excluded.total_turnover, recon_daily_summary.total_turnover),
                        realized_pnl         = COALESCE(excluded.realized_pnl, recon_daily_summary.realized_pnl),
                        starting_equity      = COALESCE(excluded.starting_equity, recon_daily_summary.starting_equity),
                        cash_flow            = COALESCE(excluded.cash_flow, recon_daily_summary.cash_flow),
                        commission           = COALESCE(excluded.commission, recon_daily_summary.commission),
                        ending_equity        = COALESCE(excluded.ending_equity, recon_daily_summary.ending_equity),
                        frozen_margin        = COALESCE(excluded.frozen_margin, recon_daily_summary.frozen_margin),
                        unrealized_pnl       = COALESCE(excluded.unrealized_pnl, recon_daily_summary.unrealized_pnl),
                        alerts_count         = COALESCE(excluded.alerts_count, recon_daily_summary.alerts_count),
                        discrepancies_count  = COALESCE(excluded.discrepancies_count, recon_daily_summary.discrepancies_count),
                        status               = COALESCE(excluded.status, recon_daily_summary.status),
                        created_at           = recon_daily_summary.created_at
                    """,
                    (
                        trade_date,
                        int(summary_data.get("total_orders", 0)) if "total_orders" in summary_data else None,
                        int(summary_data.get("total_trades", 0)) if "total_trades" in summary_data else None,
                        int(summary_data.get("total_volume", 0)) if "total_volume" in summary_data else None,
                        float(summary_data.get("total_turnover", 0.0)) if "total_turnover" in summary_data else None,
                        float(summary_data.get("realized_pnl", 0.0)) if "realized_pnl" in summary_data else None,
                        float(summary_data.get("starting_equity", 0.0)) if "starting_equity" in summary_data else None,
                        float(summary_data.get("cash_flow", 0.0)) if "cash_flow" in summary_data else None,
                        float(summary_data.get("commission", 0.0)) if "commission" in summary_data else None,
                        float(summary_data.get("ending_equity", 0.0)) if "ending_equity" in summary_data else None,
                        float(summary_data.get("frozen_margin", 0.0)) if "frozen_margin" in summary_data else None,
                        float(summary_data.get("unrealized_pnl", 0.0)) if "unrealized_pnl" in summary_data else None,
                        int(summary_data.get("alerts_count", 0)) if "alerts_count" in summary_data else None,
                        int(summary_data.get("discrepancies_count", 0)) if "discrepancies_count" in summary_data else None,
                        summary_data.get("status", "OK") if "status" in summary_data else None,
                        now,
                    ),
                )
                conn.commit()

    # ---- 持仓快照 -------------------------------------------------

    def get_last_position_snapshot(self, trade_date: str) -> Optional[dict]:
        """
        获取指定交易日的持仓快照列表。

        Args:
            trade_date: 交易日期字符串（YYYY-MM-DD 北京时间）

        Returns:
            包含快照记录的列表（每条含 symbol/exchange/direction/
            today_volume/yd_volume/total_volume/avg_price/
            unrealized_pnl/market_value/frozen_margin/snapshot_type/
            recorded_at），无快照时返回 None
        """
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT snapshot_uuid, trade_date, symbol, exchange,
                           direction, today_volume, yd_volume, total_volume,
                           avg_price, unrealized_pnl, market_value,
                           frozen_margin, snapshot_type, recorded_at
                    FROM recon_position_snapshots
                    WHERE trade_date = ?
                    ORDER BY recorded_at DESC
                    """,
                    (trade_date,),
                ).fetchall()
                if not rows:
                    return None
                return [dict(row) for row in rows]

    def check_recovery_mode(self) -> str:
        """
        判断当前是否处于重启恢复模式。

        Returns:
            "NORMAL"          — 上次快照在 24 小时内，无需恢复
            "RECOVERY_NEEDED" — 上次快照超过 24 小时，需要从快照恢复
        """
        now_dt = datetime.now(pytz.timezone("Asia/Shanghai"))
        with self._lock:
            with self._connect() as conn:
                latest = conn.execute(
                    "SELECT MAX(recorded_at) FROM recon_position_snapshots"
                ).fetchone()[0]
                if latest is None:
                    return "RECOVERY_NEEDED"
                try:
                    latest_dt = parse_cst(latest)
                    # 确保 latest_dt 有时区信息
                    if latest_dt.tzinfo is None:
                        latest_dt = pytz.timezone("Asia/Shanghai").localize(latest_dt)
                    diff_hours = (now_dt - latest_dt).total_seconds() / 3600
                except Exception:
                    # Fallback: if parse fails, trigger recovery
                    return "RECOVERY_NEEDED"
                return "NORMAL" if diff_hours < 24 else "RECOVERY_NEEDED"

    def get_or_create_daily_summary(self, trade_date: str) -> dict:
        """
        获取或创建指定交易日的对账汇总记录。

        Args:
            trade_date: 交易日期字符串（YYYY-MM-DD 北京时间）

        Returns:
            当日汇总 dict（total_orders / total_trades / total_volume /
            total_turnover / realized_pnl / starting_equity / cash_flow /
            commission / ending_equity / frozen_margin / unrealized_pnl /
            alerts_count / discrepancies_count / status / created_at）
        """
        now = now_cst()
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM recon_daily_summary WHERE trade_date = ?",
                    (trade_date,),
                ).fetchone()
                if row:
                    return dict(row)
                # 不存在则创建空白记录（确保日终快照有锚点）
                conn.execute(
                    """
                    INSERT INTO recon_daily_summary (trade_date, created_at)
                    VALUES (?, ?)
                    """,
                    (trade_date, now),
                )
                conn.commit()
                new_row = conn.execute(
                    "SELECT * FROM recon_daily_summary WHERE trade_date = ?",
                    (trade_date,),
                ).fetchone()
                return dict(new_row) if new_row else {}

    def recover_positions_from_snapshot(
        self,
        snapshot_date: str,
        bridge: Any = None,
    ) -> int:
        """
        从指定日期的持仓快照恢复持仓，写入 recon_positions 表。

        恢复逻辑（三档兜底）：
        1. 优先用 bridge（broker）实时持仓
        2. broker 无数据时用快照数据
        3. 无快照时跳过

        跨日处理：如果快照日期 < 当前日期，
        将快照的 today_volume 全部滚动为 yd_volume。

        Args:
            snapshot_date: 快照日期（YYYY-MM-DD）
            bridge: VNpyBridge 或 PaperBridge 实例（可选）

        Returns:
            恢复的持仓条数
        """
        now = now_cst()
        current_date = now[:10]  # YYYY-MM-DD
        is_cross_day = snapshot_date < current_date

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM recon_position_snapshots
                    WHERE trade_date = ?
                    """,
                    (snapshot_date,),
                ).fetchall()

                if not rows:
                    return 0

                # 从 bridge 获取实时持仓（如果有）
                broker_positions: Dict[Tuple, dict] = {}
                if bridge is not None and hasattr(bridge, "get_positions"):
                    try:
                        for pos in bridge.get_positions():
                            key = (pos["symbol"], pos["exchange"], pos["direction"])
                            broker_positions[key] = pos
                    except Exception:
                        pass  # bridge 查不到则跳过

                recovered = 0
                for row in rows:
                    snap = dict(row)
                    key = (snap["symbol"], snap["exchange"], snap["direction"])

                    if key in broker_positions:
                        # 优先用 broker 实时数据
                        bp = broker_positions[key]
                        position_data = {
                            "symbol": bp["symbol"],
                            "exchange": bp["exchange"],
                            "direction": bp["direction"],
                            "today_volume": max(0, int(bp.get("volume", 0)) - int(bp.get("yd_volume", 0))),
                            "yd_volume": int(bp.get("yd_volume", 0)),
                            "total_volume": int(bp.get("volume", 0)),
                            "avg_price": float(bp.get("price", 0.0)),
                            "unrealized_pnl": float(bp.get("pnl", 0.0)),
                            "source": "broker_recovery",
                        }
                    else:
                        # broker 无数据，用快照数据
                        if is_cross_day:
                            # 跨日：快照中的 yd_volume 已经包含了 EOD 滚动后的总持仓
                            # （EOD 快照：today=0, yd=total），直接使用 yd_volume
                            yd_vol = int(snap["yd_volume"])
                            today_vol = 0
                        else:
                            yd_vol = int(snap["yd_volume"])
                            today_vol = int(snap["today_volume"])

                        position_data = {
                            "symbol": snap["symbol"],
                            "exchange": snap["exchange"],
                            "direction": snap["direction"],
                            "today_volume": today_vol,
                            "yd_volume": yd_vol,
                            "total_volume": today_vol + yd_vol,
                            "avg_price": float(snap["avg_price"]),
                            "unrealized_pnl": float(snap["unrealized_pnl"]),
                            "source": "snapshot_recovery",
                        }

                    self.record_position(position_data)
                    recovered += 1

                return recovered

    def trigger_daily_snapshots(
        self,
        bridge: Any = None,
        snapshot_type: str = "EOD",
    ) -> int:
        """
        将当前持仓写入 recon_position_snapshots 表（日终快照）。

        Args:
            bridge: VNpyBridge 或 PaperBridge 实例（可选，为 None 时跳过 broker 查询）
            snapshot_type: 快照类型标识（"EOD"=日终 / "INTRADAY"=盘中 / "PRE_TRADE"=交易前）

        Returns:
            写入的快照条数
        """
        now = now_cst()
        trade_date = now[:10]

        with self._lock:
            with self._connect() as conn:
                # 先删除同一类型的旧快照（同一交易日同一类型只保留一份）
                conn.execute(
                    """
                    DELETE FROM recon_position_snapshots
                    WHERE trade_date = ? AND snapshot_type = ?
                    """,
                    (trade_date, snapshot_type),
                )

                rows = []
                # 从 bridge 获取实时持仓
                if bridge is not None and hasattr(bridge, "get_positions"):
                    try:
                        rows = bridge.get_positions()
                    except Exception:
                        rows = []

                count = 0
                for pos in rows:
                    # 跨日滚动：EOD 时 today→yd
                    if snapshot_type == "EOD":
                        today_vol = 0
                        yd_vol = int(pos.get("volume", 0))
                    else:
                        today_vol = max(0, int(pos.get("volume", 0)) - int(pos.get("yd_volume", 0)))
                        yd_vol = int(pos.get("yd_volume", 0))

                    total_vol = today_vol + yd_vol
                    avg_price = float(pos.get("price", 0.0))
                    unreal_pnl = float(pos.get("pnl", 0.0))

                    # 每个持仓生成唯一 snapshot_uuid（包含品种+方向避免冲突）
                    snapshot_uuid = (
                        f"{trade_date}_{snapshot_type}_"
                        f"{pos['symbol']}_{pos['exchange']}_{pos['direction']}"
                    )

                    conn.execute(                        """
                        INSERT INTO recon_position_snapshots
                        (snapshot_uuid, trade_date, symbol, exchange, direction,
                         today_volume, yd_volume, total_volume, avg_price,
                         unrealized_pnl, market_value, frozen_margin,
                         snapshot_type, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            snapshot_uuid,
                            trade_date,
                            pos["symbol"],
                            pos["exchange"],
                            pos["direction"],
                            today_vol,
                            yd_vol,
                            total_vol,
                            avg_price,
                            unreal_pnl,
                            avg_price * total_vol if total_vol > 0 else 0.0,
                            0.0,  # frozen_margin 暂不填
                            snapshot_type,
                            now,
                        ),
                    )
                    count += 1

                conn.commit()
                return count


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_recon_engine: Optional[ReconciliationEngine] = None
_recon_engine_lock = threading.Lock()


def get_reconciliation_engine() -> ReconciliationEngine:
    """
    获取全局 ReconciliationEngine 单例。

    使用线程锁保护单例创建过程，避免多线程并发创建多个实例。

    Returns:
        ReconciliationEngine 实例
    """
    global _recon_engine
    if _recon_engine is None:
        with _recon_engine_lock:
            # 双重检查：获取锁后再次确认，避免多线程竞争
            if _recon_engine is None:
                _recon_engine = ReconciliationEngine()
    return _recon_engine
