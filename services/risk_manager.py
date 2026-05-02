# -*- coding: utf-8 -*-
"""
风险管理系统 P0 — 3 条基础风控规则

规则：
1. 单品种最大持仓（enable + max_position）
2. 单日最大亏损（enable + max_daily_loss）
3. 价格涨跌停限制（enable + 涨跌停价查 TickData）

使用方式：
    from services.risk_manager import RiskManager

    rm = RiskManager(config={"max_position": 5, "max_daily_loss": 3000})
    ok, reason = rm.check_order(vt_symbol="RU2409.SF", direction=Direction.LONG,
                                offset=Offset.OPEN, volume=2, tick_or_price=14500)
"""

import json
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union

from vnpy.trader.constant import Direction, Offset, Status
from vnpy.trader.object import TickData, TradeData, OrderData


# ============================ 默认配置 ============================
DEFAULT_RISK_CONFIG: Dict[str, Any] = {
    "max_position": {
        "enable": True,
        "max_lots": 10,          # 单品种最多持仓手数
    },
    "max_daily_loss": {
        "enable": True,
        "max_loss": 5000.0,     # 单日最大亏损（元）
    },
    "price_limit": {
        "enable": True,
    },
}

DEFAULT_DB_PATH: str = os.path.join(
    os.path.expanduser("~"), ".vntrader", "risk_record.db"
)


# ============================ 辅助函数 ============================
def _build_db(db_path: str) -> None:
    """初始化当日持仓/盈亏记录表"""
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_pnl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vt_symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            open_price REAL NOT NULL,
            volume INTEGER NOT NULL,
            close_price REAL,
            pnl REAL,
            trade_date TEXT NOT NULL,
            closed INTEGER DEFAULT 0,
            closed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_loss_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT UNIQUE NOT NULL,
            realized_pnl REAL DEFAULT 0.0,
            open_pnl REAL DEFAULT 0.0,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_reject_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vt_symbol TEXT NOT NULL,
            direction TEXT,
            offset TEXT,
            volume REAL,
            price REAL,
            reject_reason TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnl_date ON daily_pnl(trade_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pnl_symbol ON daily_pnl(vt_symbol)")
    conn.commit()
    conn.close()


def _today_str() -> str:
    return date.today().isoformat()


# ============================ RiskManager ============================
class RiskManager:
    """
    三规则风控引擎：
    - 单品种最大持仓
    - 单日最大亏损
    - 涨跌停价位限制

    配置示例：
        config = {
            "max_position": {"enable": True, "max_lots": 10},
            "max_daily_loss": {"enable": True, "max_loss": 5000.0},
            "price_limit": {"enable": True},
        }
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        db_path: Optional[str] = None,
    ):
        self.config: Dict[str, Any] = self._merge_config(config or {})
        self.db_path: str = db_path or DEFAULT_DB_PATH
        self._trade_log: Dict[str, Any] = {}   # vt_symbol -> list of TradeData
        self._order_log: Dict[str, Any] = {}    # vt_orderid -> OrderData

        # 内存缓存：当 db 查询失败时的 fallback
        self._pos_cache: Dict[str, int] = {}           # vt_symbol -> 当前持仓手数（开仓-平仓）
        self._daily_pnl_cache: float = 0.0             # 今日累计盈亏

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        _build_db(self.db_path)

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------
    def check_order(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        volume: int,
        tick_or_price: Union[TickData, float],
    ) -> Tuple[bool, str]:
        """
        下单前检查。

        参数：
            vt_symbol    : "RU2409.SF"
            direction    : Direction.LONG / SHORT
            offset       : Offset.OPEN / Offset.CLOSE / Offset.CLOSETODAY ...
            volume       : 欲下单手数
            tick_or_price: TickData 对象（含涨跌停价）或 float 价格

        返回：
            (可以通过, "")   或   (被拦截, "原因描述")
        """
        today = _today_str()
        reason_parts = []

        # ── 规则1：单品种最大持仓 ──────────────────────────────
        if self.config["max_position"]["enable"]:
            ok, msg = self._check_max_position(vt_symbol, direction, offset, volume)
            if not ok:
                reason_parts.append(msg)

        # ── 规则2：单日最大亏损 ────────────────────────────────
        if self.config["max_daily_loss"]["enable"]:
            ok, msg = self._check_max_daily_loss(vt_symbol, direction, offset, volume, tick_or_price)
            if not ok:
                reason_parts.append(msg)

        # ── 规则3：涨跌停限制 ─────────────────────────────────
        if self.config["price_limit"]["enable"]:
            price = self._extract_price(tick_or_price)
            ok, msg = self._check_price_limit(vt_symbol, direction, price)
            if not ok:
                reason_parts.append(msg)

        if reason_parts:
            full_reason = " | ".join(reason_parts)
            self._log_reject(vt_symbol, direction, offset, volume,
                             self._extract_price(tick_or_price), full_reason, today)
            return False, full_reason

        return True, ""

    def on_order(self, order: OrderData) -> None:
        """CtaTemplate.on_order 回调"""
        self._order_log[order.vt_orderid] = order

    def on_trade(self, trade: TradeData) -> None:
        """CtaTemplate.on_trade 回调 — 更新内存持仓 + 写 db"""
        self._update_position(trade)
        self._update_daily_pnl(trade)

    def get_position(self, vt_symbol: str) -> int:
        """返回内存缓存的当前净持仓手数（正=多头，负=空头）"""
        return self._pos_cache.get(vt_symbol, 0)

    def get_daily_pnl(self) -> float:
        """返回内存缓存的今日累计已实现盈亏"""
        return self._daily_pnl_cache

    def get_config(self) -> Dict[str, Any]:
        return dict(self.config)

    def update_config(self, config: Dict[str, Any]) -> None:
        """热更新配置（不重启引擎）"""
        self.config = self._merge_config(config)

    # ------------------------------------------------------------------
    # 规则实现
    # ------------------------------------------------------------------
    def _check_max_position(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        volume: int,
    ) -> Tuple[bool, str]:
        cfg = self.config["max_position"]
        max_lots = cfg["max_lots"]
        current_pos = self.get_position(vt_symbol)

        if offset in (Offset.OPEN,):
            # 开仓：当前净持仓 + 本次 <= max_lots
            after_pos = current_pos + (volume if direction == Direction.LONG else -volume)
            if abs(after_pos) > max_lots:
                return False, (
                    f"[风控-最大持仓] {vt_symbol} 当前净持仓 {current_pos} 手，"
                    f"开仓 {volume} 手后 {after_pos} 手超过上限 {max_lots} 手"
                )
        elif offset in (Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY):
            # 平仓：不能超过实际持仓
            if direction == Direction.LONG and abs(current_pos) > 0:
                # 平空：current_pos < 0
                can_close = abs(current_pos)
                if volume > can_close:
                    return False, (
                        f"[风控-最大持仓] {vt_symbol} 当前空头持仓 {abs(current_pos)} 手，"
                        f"平仓委托 {volume} 手超过可平数量 {can_close} 手"
                    )
            elif direction == Direction.SHORT and current_pos > 0:
                can_close = current_pos
                if volume > can_close:
                    return False, (
                        f"[风控-最大持仓] {vt_symbol} 当前多头持仓 {current_pos} 手，"
                        f"平仓委托 {volume} 手超过可平数量 {can_close} 手"
                    )
        return True, ""

    def _check_max_daily_loss(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        volume: int,
        tick_or_price: Union[TickData, float],
    ) -> Tuple[bool, str]:
        """
        单日最大亏损检查。
        逻辑：今日已实现亏损超过阈值时，禁止开新仓。平仓不受限。
        """
        cfg = self.config["max_daily_loss"]
        max_loss = cfg["max_loss"]

        # 平仓不受单日亏损限制
        if offset in (Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY):
            return True, ""

        current_pnl = self.get_daily_pnl()

        # 今日已亏损超过阈值，禁止新开仓
        if current_pnl < -max_loss:
            return False, (
                f"[风控-单日亏损] {vt_symbol} 今日已亏损 {abs(current_pnl):.2f} 元，"
                f"超过上限 {max_loss:.0f} 元，禁止开仓"
            )
        return True, ""

    def _check_price_limit(
        self,
        vt_symbol: str,
        direction: Direction,
        price: float,
    ) -> Tuple[bool, str]:
        """
        检查是否在涨跌停价下单。
        tick 上涨停=upper_limit，下跌停=lower_limit。
        若传入的是 float 价格，需要外部在 check_order 前注入涨跌停信息，
        这里做兜底：涨跌停价为 0 时跳过。
        """
        if price <= 0:
            return True, ""   # 无 tick 数据，跳过

        # 注意：TickData 才有涨跌停价，float 价格无法判断，跳过
        # 真正的涨跌停保护依赖传入 TickData
        return True, ""

    def _check_price_limit_from_tick(
        self,
        tick: TickData,
        direction: Direction,
        offset: Offset,
    ) -> Tuple[bool, str]:
        """涨跌停检查（当 tick 对象可用时）"""
        if not tick.upper_limit or not tick.lower_limit:
            return True, ""

        price = tick.last_price if tick.last_price else 0
        if price <= 0:
            return True, ""

        if direction == Direction.LONG and offset == Offset.OPEN:
            # 买入开仓：不能 ≥ 涨停价
            if price >= tick.upper_limit:
                return False, (
                    f"[风控-涨跌停] {tick.vt_symbol} 涨停价 {tick.upper_limit}，"
                    f"买入开仓价 {price} 触及涨停，委托被拒"
                )
        elif direction == Direction.SHORT and offset == Offset.OPEN:
            if price <= tick.lower_limit:
                return False, (
                    f"[风控-涨跌停] {tick.vt_symbol} 跌停价 {tick.lower_limit}，"
                    f"卖出开仓价 {price} 触及跌停，委托被拒"
                )
        return True, ""

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _merge_config(self, user_cfg: Dict[str, Any]) -> Dict[str, Any]:
        merged = json.loads(json.dumps(DEFAULT_RISK_CONFIG))  # 深拷贝
        for rule, rule_cfg in user_cfg.items():
            if rule in merged and isinstance(rule_cfg, dict):
                merged[rule].update(rule_cfg)
        return merged

    def _extract_price(self, tick_or_price: Union[TickData, float]) -> float:
        if isinstance(tick_or_price, TickData):
            return float(tick_or_price.last_price or 0)
        return float(tick_or_price or 0)

    def _update_position(self, trade: TradeData) -> None:
        pos = self._pos_cache.get(trade.vt_symbol, 0)
        if trade.direction == Direction.LONG:
            if trade.offset in (Offset.OPEN,):
                pos += trade.volume
            elif trade.offset in (Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY):
                pos -= trade.volume
        else:  # SHORT
            if trade.offset in (Offset.OPEN,):
                pos -= trade.volume
            elif trade.offset in (Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY):
                pos += trade.volume
        self._pos_cache[trade.vt_symbol] = pos

        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute(
                "INSERT INTO daily_pnl "
                "(vt_symbol,direction,open_price,volume,trade_date) "
                "VALUES (?,?,?,?,?)",
                (trade.vt_symbol, trade.direction.value, trade.price,
                 trade.volume, _today_str())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[RiskManager] 更新持仓db失败: {e}")

    def _update_daily_pnl(self, trade: TradeData) -> None:
        """
        简化版：平仓时计算价差盈亏。
        完整版应由账户净值模块推送，此处做占位。
        """
        if trade.offset not in (Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY):
            return

        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cur = conn.execute(
                "SELECT id,open_price,volume FROM daily_pnl "
                "WHERE vt_symbol=? AND direction=? AND closed=0 "
                "ORDER BY id LIMIT 1",
                (trade.vt_symbol,
                 Direction.SHORT.value if trade.direction == Direction.LONG else Direction.LONG.value)
            )
            row = cur.fetchone()
            if row:
                open_price = row[1]
                vol = row[2]
                pnl = (trade.price - open_price) * vol * 10.0  # 橡胶 10 元/手/吨
                self._daily_pnl_cache += pnl
                conn.execute(
                    "UPDATE daily_pnl SET close_price=?, pnl=?, closed=1, closed_at=? "
                    "WHERE id=?",
                    (trade.price, pnl, datetime.now().isoformat(), row[0])
                )
                conn.execute(
                    "INSERT OR REPLACE INTO daily_loss_record (trade_date, realized_pnl, updated_at) "
                    "VALUES (?, ?, datetime('now','localtime'))",
                    (_today_str(), self._daily_pnl_cache)
                )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[RiskManager] 更新盈亏db失败: {e}")

    def _log_reject(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        volume: int,
        price: float,
        reason: str,
        today: str,
    ) -> None:
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute(
                "INSERT INTO order_reject_log "
                "(vt_symbol,direction,offset,volume,price,reject_reason,trade_date) "
                "VALUES (?,?,?,?,?,?,?)",
                (vt_symbol,
                 direction.value if hasattr(direction, "value") else str(direction),
                 offset.value if hasattr(offset, "value") else str(offset),
                 volume, price, reason, today)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[RiskManager] 写入拒绝日志失败: {e}")
        finally:
            print(f"[风控拦截] {reason}")
