# -*- coding: utf-8 -*-
"""
SignalBridge — 文件系统事件驱动桥接器

功能：
1. 使用 watchdog 监控宏观信号 CSV 目录
2. 当 CSV 文件创建/修改时，解析并发布 EVENT_MACRO_SIGNAL 事件到 EventEngine
3. 提供 fallback 轮询机制（watchdog 失败时回退到 60 秒轮询）
4. 策略通过 get_latest_signal(symbol) 获取内存缓存信号，避免重复读取文件

使用方式：
    from services.signal_bridge import SignalBridge, EVENT_MACRO_SIGNAL

    bridge = SignalBridge(event_engine, csv_dir="D:/futures_v6/macro_engine/output")
    bridge.start()
    # ... 策略订阅 EVENT_MACRO_SIGNAL 事件 ...
    bridge.stop()
"""

import csv
import os
import re
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from vnpy.event import EventEngine, Event

# ============================ 自定义事件类型 ============================
EVENT_MACRO_SIGNAL: str = "eMacroSignal"

# ============================ 默认配置 ============================
DEFAULT_POLL_INTERVAL: int = 60  # fallback 轮询间隔（秒）
CSV_PATTERN: re.Pattern = re.compile(r"^(?P<symbol>[A-Za-z]+)_macro_daily_(?P<date>\d{8})\.csv$")


# ============================ 辅助函数 ============================
def _extract_symbol_from_filename(filename: str) -> Optional[str]:
    """从 CSV 文件名提取品种代码，如 AU_macro_daily_20260424.csv -> AU"""
    m = CSV_PATTERN.match(filename)
    if m:
        return m.group("symbol").upper()
    return None


def _parse_csv_signal(csv_path: Path) -> Optional[Dict[str, Any]]:
    """
    解析单个 CSV 文件，提取 SUMMARY 行和 FACTOR 行。
    返回 dict：
        {
            "symbol": "AU",
            "date": "2026-04-24",
            "direction": "LONG",
            "score": 0.3095,
            "confidence": "MEDIUM",
            "factors": [
                {
                    "factorCode": "AU_CFTC_NC",
                    "factorName": "AU_CFTC_NC",
                    "rawValue": 45530.0,
                    "normalizedScore": 0.0,
                    "weight": 0.0156,
                    "contribution": 0.0,
                    "contributionPolarity": "positive",
                    "icValue": 0.0,
                },
                ...
            ],
            "source_file": "...",
            "updated_at": "2026-04-24T00:10:16+08:00",
        }
    """
    if not csv_path.exists():
        return None

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"[SignalBridge] 读取 CSV 失败: {csv_path} -> {e}")
        return None

    summary: Optional[Dict[str, Any]] = None
    factors: List[Dict[str, Any]] = []

    for row in rows:
        # 兼容 camelCase(rowType) 和 snake_case(row_type)
        row_type = row.get("rowType", "") or row.get("row_type", "")
        # 兼容 BOM 前缀的 symbol 字段
        row_symbol = row.get("symbol", "") or row.get("\ufeffsymbol", "")

        if row_type == "SUMMARY":
            # 兼容 compositeScore / composite_score
            score_str = row.get("compositeScore", "") or row.get("composite_score", "")
            score = float(score_str) if score_str else 0.0
            summary = {
                "symbol": row_symbol.upper(),
                "date": row.get("date", ""),
                "direction": row.get("direction", "NEUTRAL"),
                "score": score,
                "confidence": row.get("confidence", "MEDIUM"),
                "updated_at": row.get("updatedAt", "") or row.get("updated_at", ""),
            }
        elif row_type == "FACTOR":
            factor = {
                "factorCode": row.get("factorCode", "") or row.get("factor_code", ""),
                "factorName": row.get("factorName", "") or row.get("factor_name", ""),
                "rawValue": _safe_float(row.get("rawValue", "") or row.get("raw_value", "")),
                "normalizedScore": _safe_float(row.get("normalizedScore", "") or row.get("normalized_score", "")),
                "weight": _safe_float(row.get("weight", "")),
                "contribution": _safe_float(row.get("contribution", "")),
                "contributionPolarity": row.get("contributionPolarity", "") or row.get("contribution_polarity", ""),
                "icValue": _safe_float(row.get("icValue", "") or row.get("ic_value", "")),
            }
            factors.append(factor)

    if summary is None:
        return None

    summary["factors"] = factors
    summary["source_file"] = str(csv_path)
    summary["parsed_at"] = datetime.now().isoformat()
    return summary


def _safe_float(val: Any) -> float:
    """安全转换 float，空值返回 0.0"""
    if val is None or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# ============================ SignalBridge ============================
class SignalBridge:
    """
    宏观信号桥接器

    - 启动 watchdog 监控 CSV 目录
    - 文件变更时自动解析并发布 EVENT_MACRO_SIGNAL 事件
    - 提供内存缓存，策略通过 get_latest_signal(symbol) 获取最新信号
    - watchdog 失败时自动回退到 60 秒轮询
    """

    def __init__(self, event_engine: EventEngine, csv_dir: str):
        self.event_engine: EventEngine = event_engine
        self.csv_dir: Path = Path(csv_dir)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存: {symbol: signal_dict}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        # watchdog 相关
        self._observer = None
        self._watchdog_available: bool = False
        self._fallback_thread: Optional[threading.Thread] = None
        self._fallback_running: bool = False
        self._poll_interval: int = DEFAULT_POLL_INTERVAL

        # 文件修改时间记录，用于 fallback 轮询检测变更
        self._file_mtimes: Dict[str, float] = {}

    # -------------------- 公共接口 --------------------
    def start(self) -> None:
        """启动桥接器：优先 watchdog，失败则 fallback 轮询"""
        print(f"[SignalBridge] 启动，CSV 目录: {self.csv_dir}")
        self._scan_all_csv()  # 启动时先扫描一遍现有文件

        if self._try_start_watchdog():
            print("[SignalBridge] watchdog 监控已启动")
        else:
            print("[SignalBridge] watchdog 不可用，启动 fallback 轮询（60s）")
            self._start_fallback_poll()

    def stop(self) -> None:
        """停止桥接器：关闭 watchdog 和 fallback 轮询"""
        print("[SignalBridge] 停止")
        self._stop_watchdog()
        self._stop_fallback_poll()

    def get_latest_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取指定品种的最新宏观信号（内存缓存，不读取文件）

        Args:
            symbol: 品种代码，如 "AU", "RU"

        Returns:
            信号字典，无缓存时返回 None
        """
        with self._lock:
            return self._cache.get(symbol.upper())

    def get_all_signals(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存的信号副本"""
        with self._lock:
            return dict(self._cache)

    def get_latest_direction(self, symbol: str) -> Optional[str]:
        """
        获取指定品种的最新宏观方向
        
        Args:
            symbol: 品种代码，如 "AU", "RU"
            
        Returns:
            方向字符串: "LONG", "SHORT", "NEUTRAL" 或 None
        """
        signal = self.get_latest_signal(symbol)
        if signal:
            return signal.get("direction", "NEUTRAL")
        return None
    
    def get_latest_score(self, symbol: str) -> Optional[float]:
        """
        获取指定品种的最新宏观评分
        
        Args:
            symbol: 品种代码，如 "AU", "RU"
            
        Returns:
            评分值 (-1 ~ 1) 或 None
        """
        signal = self.get_latest_signal(symbol)
        if signal:
            return signal.get("score", 0.0)
        return None

    # -------------------- 内部方法：watchdog --------------------
    def _try_start_watchdog(self) -> bool:
        """尝试启动 watchdog，返回是否成功"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("[SignalBridge] watchdog 未安装")
            return False

        class _CsvHandler(FileSystemEventHandler):
            def __init__(self, bridge: "SignalBridge"):
                self.bridge = bridge

            def on_created(self, event):
                if not event.is_directory:
                    self.bridge._handle_file_change(Path(event.src_path))

            def on_modified(self, event):
                if not event.is_directory:
                    self.bridge._handle_file_change(Path(event.src_path))

        try:
            self._observer = Observer()
            handler = _CsvHandler(self)
            self._observer.schedule(handler, str(self.csv_dir), recursive=False)
            self._observer.start()
            self._watchdog_available = True
            return True
        except Exception as e:
            print(f"[SignalBridge] watchdog 启动失败: {e}")
            self._observer = None
            self._watchdog_available = False
            return False

    def _stop_watchdog(self) -> None:
        """停止 watchdog"""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=5.0)
            except Exception as e:
                print(f"[SignalBridge] watchdog 停止异常: {e}")
            finally:
                self._observer = None
                self._watchdog_available = False

    # -------------------- 内部方法：fallback 轮询 --------------------
    def _start_fallback_poll(self) -> None:
        """启动 fallback 轮询线程"""
        self._fallback_running = True
        self._fallback_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._fallback_thread.start()

    def _stop_fallback_poll(self) -> None:
        """停止 fallback 轮询线程"""
        self._fallback_running = False
        if self._fallback_thread is not None:
            self._fallback_thread.join(timeout=self._poll_interval + 5)
            self._fallback_thread = None

    def _poll_loop(self) -> None:
        """轮询循环：检测文件修改时间变化"""
        while self._fallback_running:
            try:
                self._scan_all_csv()
            except Exception as e:
                print(f"[SignalBridge] fallback 轮询异常: {e}")
            # 分段 sleep，便于快速退出
            for _ in range(self._poll_interval):
                if not self._fallback_running:
                    break
                time.sleep(1)

    # -------------------- 内部方法：文件处理 --------------------
    def _handle_file_change(self, file_path: Path) -> None:
        """处理单个文件变更事件（watchdog 回调或轮询调用）"""
        if not file_path.suffix.lower() == ".csv":
            return
        symbol = _extract_symbol_from_filename(file_path.name)
        if symbol is None:
            return

        signal = _parse_csv_signal(file_path)
        if signal is None:
            return

        self._publish_signal(signal)

    def _scan_all_csv(self) -> None:
        """扫描目录下所有 CSV，检测变更并更新缓存"""
        if not self.csv_dir.exists():
            return

        for file_path in self.csv_dir.glob("*.csv"):
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                continue

            key = str(file_path)
            prev_mtime = self._file_mtimes.get(key)
            if prev_mtime is not None and mtime <= prev_mtime:
                continue  # 未变更

            self._file_mtimes[key] = mtime
            self._handle_file_change(file_path)

    def _publish_signal(self, signal: Dict[str, Any]) -> None:
        """发布 EVENT_MACRO_SIGNAL 事件并更新缓存"""
        symbol = signal.get("symbol", "").upper()
        if not symbol:
            return

        with self._lock:
            self._cache[symbol] = signal

        event = Event(type=EVENT_MACRO_SIGNAL, data=signal)
        self.event_engine.put(event)
        print(f"[SignalBridge] 发布信号: {symbol} -> {signal['direction']}, score={signal['score']:.4f}")
