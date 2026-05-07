# -*- coding: utf-8 -*-
"""
SignalBridge — CSV 文件变更 → WebSocket 实时推送

功能：
1. 使用 watchdog 监控宏观信号 CSV 目录（fallback: asyncio 定时轮询）
2. CSV 变更时解析信号数据，通过 WebSocket 推送到前端
3. 支持 USE_MOCK 开关（Mock 模式直接推送模拟数据，不 watch 文件）
4. 保留 vnpy EventEngine 事件发布（向后兼容策略层）

WebSocket 端点：/ws/signal
推送格式：
    {
        "type": "signal_update",
        "symbol": "RU",
        "data": {
            "compositeScore": 0.6323,
            "direction": "LONG",
            "factorDetails": [...],
            "updatedAt": "2026-05-06T14:30:00"
        }
    }

使用方式（独立运行测试）：
    python services/signal_bridge.py          # 正常模式
    python services/signal_bridge.py --mock   # Mock 模式

集成到 API 服务器：
    from services.signal_bridge import SignalBridge, init_signal_ws
    init_signal_ws(app, csv_dir="D:/futures_v6/macro_engine/output")
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# 路径设置
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "macro_engine"))

try:
    from config.paths import OUTPUT as DEFAULT_CSV_DIR
    _DEFAULT_CSV_DIR_STR = str(DEFAULT_CSV_DIR)
except Exception:
    _DEFAULT_CSV_DIR_STR = str(_PROJECT_ROOT / "macro_engine" / "output")

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SignalBridge] %(levelname)s %(message)s",
)
logger = logging.getLogger("SignalBridge")

# ---------------------------------------------------------------------------
# 常量 / 配置
# ---------------------------------------------------------------------------
USE_MOCK: bool = os.environ.get("SIGNAL_BRIDGE_MOCK", "0") == "1"

DEFAULT_POLL_INTERVAL: int = 5          # fallback 轮询间隔（秒）
MOCK_PUSH_INTERVAL: int = 10            # Mock 模式推送间隔（秒）
WS_HEARTBEAT_INTERVAL: int = 30         # WebSocket 心跳间隔（秒）

CSV_PATTERN: re.Pattern = re.compile(
    r"^(?P<symbol>[A-Za-z]+)_macro_daily_(?P<date>\d{8})\.csv$"
)

# vnpy 事件类型（可选，向后兼容）
try:
    # 尝试从已有 signal_bridge 导入（旧版兼容）
    from services.signal_bridge import EVENT_MACRO_SIGNAL  # type: ignore
except Exception:
    EVENT_MACRO_SIGNAL: str = "eMacroSignal"

# ---------------------------------------------------------------------------
# Mock 数据生成
# ---------------------------------------------------------------------------
_MOCK_SYMBOLS = ["RU", "AU", "AG", "CU", "RB", "BR", "NI", "NR"]
_MOCK_DIRECTIONS = ["LONG", "SHORT", "NEUTRAL"]


def _generate_mock_signal(symbol: str) -> Dict[str, Any]:
    """生成一条模拟信号数据"""
    import random
    score = round(random.uniform(-1.0, 1.0), 4)
    if score > 0.15:
        direction = "LONG"
    elif score < -0.15:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    factors = [
        {
            "factorCode": f"{symbol}_FUT_OI",
            "factorName": f"{symbol}期货持仓量",
            "rawValue": round(random.uniform(50000, 300000), 0),
            "normalizedScore": round(random.uniform(-3, 3), 4),
            "weight": 0.15,
            "contribution": round(random.uniform(-0.3, 0.3), 4),
            "contributionPolarity": "positive",
            "icValue": round(random.uniform(-0.1, 0.3), 4),
        },
        {
            "factorCode": f"{symbol}_INV_TOTAL",
            "factorName": f"{symbol}总库存",
            "rawValue": round(random.uniform(10000, 200000), 0),
            "normalizedScore": round(random.uniform(-3, 3), 4),
            "weight": 0.12,
            "contribution": round(random.uniform(-0.2, 0.2), 4),
            "contributionPolarity": "negative",
            "icValue": round(random.uniform(-0.1, 0.2), 4),
        },
        {
            "factorCode": f"{symbol}_SPOT_PRICE",
            "factorName": f"{symbol}现货价格",
            "rawValue": round(random.uniform(5000, 50000), 0),
            "normalizedScore": round(random.uniform(-3, 3), 4),
            "weight": 0.10,
            "contribution": round(random.uniform(-0.2, 0.2), 4),
            "contributionPolarity": "positive",
            "icValue": round(random.uniform(-0.1, 0.2), 4),
        },
    ]

    now = datetime.now()
    return {
        "type": "signal_update",
        "symbol": symbol,
        "data": {
            "compositeScore": score,
            "direction": direction,
            "factorDetails": factors,
            "updatedAt": now.isoformat(),
            "confidence": "MEDIUM",
            "factorCount": len(factors),
        },
    }


# ---------------------------------------------------------------------------
# CSV 解析
# ---------------------------------------------------------------------------
def _extract_symbol_from_filename(filename: str) -> Optional[str]:
    """从文件名提取品种代码"""
    m = CSV_PATTERN.match(filename)
    return m.group("symbol").upper() if m else None


def _safe_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def parse_csv_signal(csv_path: Path) -> Optional[Dict[str, Any]]:
    """
    解析单个 CSV 文件，返回 WebSocket 推送格式的信号字典。

    返回：
        {
            "type": "signal_update",
            "symbol": "RU",
            "data": {
                "compositeScore": 0.6323,
                "direction": "LONG",
                "factorDetails": [...],
                "updatedAt": "...",
                "confidence": "...",
                "factorCount": 14,
            }
        }
    """
    if not csv_path.exists():
        return None

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        logger.error(f"读取 CSV 失败: {csv_path} -> {e}")
        return None

    summary: Optional[Dict[str, Any]] = None
    factors: List[Dict[str, Any]] = []

    for row in rows:
        row_type = row.get("rowType", "") or row.get("row_type", "")
        row_symbol = row.get("symbol", "") or row.get("\ufeffsymbol", "")

        if row_type == "SUMMARY":
            score_str = row.get("compositeScore", "") or row.get("composite_score", "")
            score = float(score_str) if score_str else 0.0
            summary = {
                "symbol": row_symbol.upper(),
                "compositeScore": score,
                "direction": row.get("direction", "NEUTRAL"),
                "updatedAt": row.get("updatedAt", "") or row.get("updated_at", ""),
                "confidence": row.get("confidence", "MEDIUM"),
                "factorCount": _safe_float(row.get("factorCount", "") or row.get("factor_count", "")),
            }
        elif row_type == "FACTOR":
            factors.append({
                "factorCode": row.get("factorCode", "") or row.get("factor_code", ""),
                "factorName": row.get("factorName", "") or row.get("factor_name", ""),
                "rawValue": _safe_float(row.get("rawValue", "") or row.get("raw_value", "")),
                "normalizedScore": _safe_float(row.get("normalizedScore", "") or row.get("normalized_score", "")),
                "weight": _safe_float(row.get("weight", "")),
                "contribution": _safe_float(row.get("contribution", "")),
                "contributionPolarity": row.get("contributionPolarity", "") or row.get("contribution_polarity", ""),
                "icValue": _safe_float(row.get("icValue", "") or row.get("ic_value", "")),
            })

    if summary is None:
        return None

    summary["factorDetails"] = factors
    return {
        "type": "signal_update",
        "symbol": summary["symbol"],
        "data": summary,
    }


# ---------------------------------------------------------------------------
# WebSocket 连接管理器
# ---------------------------------------------------------------------------
class SignalConnectionManager:
    """管理 /ws/signal 的 WebSocket 连接"""

    def __init__(self) -> None:
        self._connections: Set[Any] = set()
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._connections)

    def add(self, ws: Any) -> None:
        with self._lock:
            self._connections.add(ws)
        logger.info(f"WS 连接 +1，当前 {len(self._connections)}")

    def remove(self, ws: Any) -> None:
        with self._lock:
            self._connections.discard(ws)
        logger.info(f"WS 连接 -1，当前 {len(self._connections)}")

    def get_all(self) -> list:
        with self._lock:
            return list(self._connections)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """广播消息到所有已连接的 WebSocket 客户端"""
        payload = json.dumps(message, ensure_ascii=False)
        stale: list = []
        for ws in self.get_all():
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.remove(ws)


# 全局连接管理器实例
ws_manager = SignalConnectionManager()


# ---------------------------------------------------------------------------
# SignalBridge 主类
# ---------------------------------------------------------------------------
class SignalBridge:
    """
    CSV → WebSocket 信号桥接器

    - watchdog 监控 CSV 目录（fallback: asyncio 轮询）
    - 文件变更时解析并通过 WebSocket 推送
    - USE_MOCK 模式：不 watch 文件，定时推送模拟数据
    - 保留 vnpy EventEngine 事件发布（可选）
    """

    def __init__(
        self,
        csv_dir: str = _DEFAULT_CSV_DIR_STR,
        event_engine: Optional[Any] = None,
        use_mock: bool = USE_MOCK,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self.csv_dir: Path = Path(csv_dir)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        self._event_engine = event_engine  # 可选，vnpy EventEngine
        self._use_mock = use_mock
        self._poll_interval = poll_interval

        # 内存缓存: {symbol: signal_dict}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        # watchdog
        self._observer: Optional[Any] = None
        self._watchdog_available: bool = False

        # asyncio 轮询任务
        self._poll_task: Optional[asyncio.Task] = None
        self._running: bool = False

        # 文件 mtime 记录
        self._file_mtimes: Dict[str, float] = {}

        # CSV 文件级缓存: {symbol: {"mtime": float, "data": dict, "loaded_at": float}}
        self._file_cache: Dict[str, Dict[str, Any]] = {}

        # 外部回调（除了 WebSocket 之外的消费者）
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []

    # ------------------------------------------------------------------ 公共接口
    def register_callback(self, cb: Callable[[Dict[str, Any]], None]) -> None:
        """注册信号回调（策略层等）"""
        self._callbacks.append(cb)

    def start(self) -> None:
        """同步启动（兼容旧接口，内部调用 asyncio）"""
        logger.info(f"启动 SignalBridge | mock={self._use_mock} | dir={self.csv_dir}")
        if self._use_mock:
            logger.info("Mock 模式：跳过文件监控，定时推送模拟数据")
            return

        # 初始扫描
        self._scan_all_csv()

        if self._try_start_watchdog():
            logger.info("watchdog 监控已启动")
        else:
            logger.info(f"watchdog 不可用，将使用 asyncio 轮询（{self._poll_interval}s）")

    async def start_async(self) -> None:
        """异步启动（推荐在 FastAPI startup 中调用）"""
        self._running = True
        logger.info(f"启动 SignalBridge (async) | mock={self._use_mock} | dir={self.csv_dir}")

        if self._use_mock:
            self._poll_task = asyncio.create_task(self._mock_push_loop())
            return

        # 初始扫描
        self._scan_all_csv()

        if not self._try_start_watchdog():
            self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop_async(self) -> None:
        """异步停止"""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._stop_watchdog()
        logger.info("SignalBridge 已停止")

    def stop(self) -> None:
        """同步停止（兼容旧接口）"""
        self._running = False
        self._stop_watchdog()
        logger.info("SignalBridge 已停止")

    def get_latest_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取指定品种最新信号（内存缓存）"""
        with self._lock:
            return self._cache.get(symbol.upper())

    def get_all_signals(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存信号"""
        with self._lock:
            return dict(self._cache)

    def get_latest_direction(self, symbol: str) -> Optional[str]:
        sig = self.get_latest_signal(symbol)
        if sig:
            data = sig.get("data", sig)
            return data.get("direction", "NEUTRAL")
        return None

    def get_latest_score(self, symbol: str) -> Optional[float]:
        sig = self.get_latest_signal(symbol)
        if sig:
            data = sig.get("data", sig)
            return data.get("compositeScore", data.get("score", 0.0))
        return None

    def get_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取指定品种信号（带文件级 mtime 缓存）。

        策略层高频调用入口（每 3 秒/品种）。
        缓存策略：检查文件 mtime，不变则返回缓存，变了才重新读取。

        返回格式与 parse_csv_signal() 一致：
            {
                "type": "signal_update",
                "symbol": "RU",
                "data": {
                    "compositeScore": 0.6323,
                    "direction": "LONG",
                    "factorDetails": [...],
                    "updatedAt": "...",
                    "confidence": "...",
                    "factorCount": 14,
                }
            }
        """
        sym = symbol.upper()
        return self._read_csv_cached(sym)

    def _read_csv_cached(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        带 mtime 检查的 CSV 缓存读取。

        - mtime 不变 → 返回缓存（无文件 IO）
        - mtime 变化或无缓存 → 读取文件并更新缓存
        - 缓存命中不打日志，miss 打 DEBUG 级别
        """
        # 查找对应 CSV 文件
        csv_path: Optional[Path] = None
        for fp in self.csv_dir.glob(f"{symbol}_macro_daily_*.csv"):
            csv_path = fp
            break

        if csv_path is None or not csv_path.exists():
            return None

        try:
            current_mtime = csv_path.stat().st_mtime
        except OSError:
            return None

        # 检查缓存
        cached = self._file_cache.get(symbol)
        if cached is not None and cached["mtime"] == current_mtime:
            return cached["data"]

        # 缓存 miss：读取文件
        logger.debug(f"CSV 缓存 miss: {symbol}，读取 {csv_path.name}")
        signal = parse_csv_signal(csv_path)
        if signal is None:
            return None

        now = time.time()
        self._file_cache[symbol] = {
            "mtime": current_mtime,
            "data": signal,
            "loaded_at": now,
        }
        return signal

    # ------------------------------------------------------------------ Mock 推送
    async def _mock_push_loop(self) -> None:
        """Mock 模式：定时推送模拟数据"""
        idx = 0
        while self._running:
            symbol = _MOCK_SYMBOLS[idx % len(_MOCK_SYMBOLS)]
            signal = _generate_mock_signal(symbol)
            await self._publish_signal(signal)
            idx += 1
            await asyncio.sleep(MOCK_PUSH_INTERVAL)

    # ------------------------------------------------------------------ watchdog
    def _try_start_watchdog(self) -> bool:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            logger.warning("watchdog 未安装，跳过")
            return False

        bridge = self

        class _CsvHandler(FileSystemEventHandler):
            def on_created(self, event: Any) -> None:
                if not event.is_directory:
                    bridge._handle_file_change(Path(event.src_path))

            def on_modified(self, event: Any) -> None:
                if not event.is_directory:
                    bridge._handle_file_change(Path(event.src_path))

        try:
            self._observer = Observer()
            self._observer.schedule(_CsvHandler(), str(self.csv_dir), recursive=False)
            self._observer.daemon = True
            self._observer.start()
            self._watchdog_available = True
            return True
        except Exception as e:
            logger.error(f"watchdog 启动失败: {e}")
            self._observer = None
            return False

    def _stop_watchdog(self) -> None:
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=5.0)
            except Exception as e:
                logger.error(f"watchdog 停止异常: {e}")
            finally:
                self._observer = None
                self._watchdog_available = False

    # ------------------------------------------------------------------ 轮询
    async def _poll_loop(self) -> None:
        """asyncio 定时轮询：每 N 秒检查文件 mtime"""
        while self._running:
            try:
                self._scan_all_csv()
            except Exception as e:
                logger.error(f"轮询异常: {e}")
            await asyncio.sleep(self._poll_interval)

    # ------------------------------------------------------------------ 文件处理
    def _handle_file_change(self, file_path: Path) -> None:
        if file_path.suffix.lower() != ".csv":
            return
        symbol = _extract_symbol_from_filename(file_path.name)
        if symbol is None:
            return

        signal = parse_csv_signal(file_path)
        if signal is None:
            return

        # 同步缓存 + 发布
        with self._lock:
            self._cache[symbol] = signal

        # 异步广播（在事件循环中调度）
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._publish_signal(signal))
        except RuntimeError:
            # 没有运行中的事件循环，用线程安全方式调度
            self._schedule_broadcast(signal)

        # vnpy EventEngine 兼容
        if self._event_engine is not None:
            try:
                from vnpy.event import Event
                # 转换为旧格式
                legacy = {
                    "symbol": signal["symbol"],
                    "direction": signal["data"]["direction"],
                    "score": signal["data"]["compositeScore"],
                    "factors": signal["data"].get("factorDetails", []),
                    "updated_at": signal["data"].get("updatedAt", ""),
                }
                self._event_engine.put(Event(type=EVENT_MACRO_SIGNAL, data=legacy))
            except Exception:
                pass

        # 外部回调
        for cb in self._callbacks:
            try:
                cb(signal)
            except Exception as e:
                logger.error(f"回调异常: {e}")

        logger.info(
            f"信号更新: {symbol} -> {signal['data']['direction']}, "
            f"score={signal['data']['compositeScore']:.4f}"
        )

    def _scan_all_csv(self) -> None:
        if not self.csv_dir.exists():
            return

        for fp in self.csv_dir.glob("*.csv"):
            try:
                mtime = fp.stat().st_mtime
            except OSError:
                continue

            key = str(fp)
            prev = self._file_mtimes.get(key)
            if prev is not None and mtime <= prev:
                continue

            self._file_mtimes[key] = mtime
            self._handle_file_change(fp)

    # ------------------------------------------------------------------ WebSocket 广播
    async def _publish_signal(self, signal: Dict[str, Any]) -> None:
        """广播信号到所有 WebSocket 客户端"""
        await ws_manager.broadcast(signal)

    def _schedule_broadcast(self, signal: Dict[str, Any]) -> None:
        """在没有 running loop 时，用线程调度广播"""
        def _run() -> None:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(ws_manager.broadcast(signal))
            finally:
                loop.close()

        t = threading.Thread(target=_run, daemon=True)
        t.start()


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
_bridge_instance: Optional[SignalBridge] = None


def get_signal_bridge() -> Optional[SignalBridge]:
    return _bridge_instance


def init_signal_ws(
    app: Any,
    csv_dir: str = _DEFAULT_CSV_DIR_STR,
    event_engine: Optional[Any] = None,
    use_mock: bool = USE_MOCK,
) -> SignalBridge:
    """
    初始化 SignalBridge 并注册 FastAPI WebSocket 端点 /ws/signal。

    在 API 服务器中调用：
        from services.signal_bridge import init_signal_ws
        init_signal_ws(app, csv_dir="D:/futures_v6/macro_engine/output")
    """
    global _bridge_instance
    _bridge_instance = SignalBridge(
        csv_dir=csv_dir,
        event_engine=event_engine,
        use_mock=use_mock,
    )

    # --- 注册 WebSocket 端点 ---
    @app.websocket("/ws/signal")
    async def ws_signal_endpoint(websocket: Any) -> None:
        from fastapi import WebSocketDisconnect
        from starlette.websockets import WebSocketState

        await websocket.accept()
        ws_manager.add(websocket)
        try:
            # 发送当前缓存的全部信号
            cached = _bridge_instance.get_all_signals()
            if cached:
                for sig in cached.values():
                    try:
                        await websocket.send_text(json.dumps(sig, ensure_ascii=False))
                    except Exception:
                        break

            # 保持连接，处理客户端消息
            while True:
                try:
                    raw = await websocket.receive_text()
                    msg = json.loads(raw)

                    if msg.get("action") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    elif msg.get("action") == "get_all":
                        all_sigs = _bridge_instance.get_all_signals()
                        for sig in all_sigs.values():
                            await websocket.send_text(json.dumps(sig, ensure_ascii=False))
                    elif msg.get("action") == "get_signal":
                        sym = msg.get("symbol", "").upper()
                        sig = _bridge_instance.get_latest_signal(sym)
                        if sig:
                            await websocket.send_text(json.dumps(sig, ensure_ascii=False))
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": f"No signal for {sym}",
                            }))
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON",
                    }))
        finally:
            ws_manager.remove(websocket)

    # --- 注册 REST 接口：获取最新信号 ---
    @app.get("/api/signal/latest/{symbol}")
    async def get_latest_signal_rest(symbol: str) -> Any:
        sig = _bridge_instance.get_latest_signal(symbol)
        if sig is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"No signal for {symbol}")
        return sig

    @app.get("/api/signal/all")
    async def get_all_signals_rest() -> Any:
        return list(_bridge_instance.get_all_signals().values())

    # --- 生命周期 ---
    @app.on_event("startup")
    async def _signal_bridge_startup() -> None:
        await _bridge_instance.start_async()
        logger.info(f"SignalBridge startup complete | ws_clients={ws_manager.count}")

    @app.on_event("shutdown")
    async def _signal_bridge_shutdown() -> None:
        await _bridge_instance.stop_async()

    return _bridge_instance


# ---------------------------------------------------------------------------
# 独立运行入口
# ---------------------------------------------------------------------------
async def _standalone_main(use_mock: bool = False) -> None:
    """独立运行：启动 WebSocket 服务器 + SignalBridge"""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
    except ImportError:
        logger.error("独立运行需要 fastapi + uvicorn，请安装：pip install fastapi uvicorn")
        sys.exit(1)

    app = FastAPI(title="SignalBridge Standalone")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    bridge = init_signal_ws(app, use_mock=use_mock)

    @app.get("/")
    async def root() -> dict:
        return {
            "service": "SignalBridge",
            "mode": "mock" if use_mock else "live",
            "ws_endpoint": "/ws/signal",
            "cached_symbols": list(bridge.get_all_signals().keys()),
        }

    logger.info(f"SignalBridge standalone 启动 | mock={use_mock}")
    logger.info("WebSocket: ws://127.0.0.1:8088/ws/signal")
    logger.info("REST:      http://127.0.0.1:8088/api/signal/all")

    config = uvicorn.Config(app, host="0.0.0.0", port=8088, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    parser = argparse.ArgumentParser(description="SignalBridge — CSV → WebSocket")
    parser.add_argument("--mock", action="store_true", help="Mock 模式（推送模拟数据）")
    parser.add_argument("--port", type=int, default=8088, help="WebSocket 端口（默认 8088）")
    args = parser.parse_args()

    use_mock = args.mock or USE_MOCK
    asyncio.run(_standalone_main(use_mock=use_mock))


if __name__ == "__main__":
    main()
