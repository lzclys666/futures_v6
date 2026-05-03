"""
事件总线 - macro_engine.event_bus
技术选型：内存队列 + JSON文件持久化
"""

import json
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Callable, Any
from collections import defaultdict
from config.paths import DOCS_DIR


class EventBus:
    """
    轻量级事件总线。
    - 发布/订阅基于内存 dict[event_type, list[callback]]
    - 事件持久化到 docs/events/YYYYMMDD.json
    """

    def __init__(self, events_dir: str | Path = None):
        events_dir = events_dir or str(DOCS_DIR / "events")
        self._events_dir = Path(events_dir)
        self._events_dir.mkdir(parents=True, exist_ok=True)

        # event_type -> [callback1, callback2, ...]
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    # ── 核心接口 ──────────────────────────────────────────────

    def publish(self, event_type: str, payload: Any) -> None:
        """
        发布事件。

        Args:
            event_type: 事件类型，如 "MARKET_DATA_ARRIVED"
            payload:     事件负载，任意可序列化对象
        """
        now = datetime.now()
        event = {
            "event_type": event_type,
            "timestamp": now.isoformat(timespec="seconds") + "+08:00",
            "payload": payload,
        }

        # 1. 触发内存订阅者
        with self._lock:
            for callback in self._subscribers.get(event_type, []):
                try:
                    callback(event)
                except Exception:
                    # 订阅者异常不影响发布
                    pass

        # 2. 追加到当日 JSON 文件
        self._append_to_daily_file(event)

    def subscribe(self, event_type: str, callback: Callable[[dict], None]) -> None:
        """
        订阅事件。

        Args:
            event_type: 要订阅的事件类型
            callback:   回调函数，签名为 (event: dict) -> None
        """
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[dict], None]) -> None:
        """退订事件。"""
        with self._lock:
            if callback in self._subscribers.get(event_type, []):
                self._subscribers[event_type].remove(callback)

    def get_events(
        self, event_type: str | None = None, since: str | None = None
    ) -> list[dict]:
        """
        获取事件历史（从当日 JSON 文件读取）。

        Args:
            event_type: 可选，筛选事件类型
            since:      可选，ISO 格式时间戳下限

        Returns:
            匹配条件的事件列表，按时间升序
        """
        daily_file = self._get_daily_path()
        if not daily_file.exists():
            return []

        try:
            with open(daily_file, "r", encoding="utf-8") as f:
                events = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

        result = []
        for ev in events:
            if event_type is not None and ev.get("event_type") != event_type:
                continue
            if since is not None and ev.get("timestamp", "") < since:
                continue
            result.append(ev)

        return result

    # ── 内部方法 ──────────────────────────────────────────────

    def _get_daily_path(self) -> Path:
        today = date.today()
        return self._events_dir / f"{today.strftime('%Y%m%d')}.json"

    def _append_to_daily_file(self, event: dict) -> None:
        daily_file = self._get_daily_path()
        events: list[dict] = []

        if daily_file.exists():
            try:
                with open(daily_file, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except (json.JSONDecodeError, IOError):
                events = []

        events.append(event)

        with open(daily_file, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)


# 全局单例
_default_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus
