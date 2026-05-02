"""
circuit_breaker.py — 多品种同向触发熔断 API

功能：
- 当 >60% 品种同向时自动触发 PENDING_CONFIRM
- 30 分钟内人工确认暂停或忽略
- 状态持久化到本地 JSON 文件

Endpoint 列表：
  GET  /api/risk/circuit_breaker            — 查询熔断状态
  POST /api/risk/circuit_breaker/trigger     — 触发熔断（内部调用）
  POST /api/risk/circuit_breaker/confirm_pause — 确认暂停交易
  POST /api/risk/circuit_breaker/dismiss     — 忽略告警，恢复正常
  POST /api/risk/circuit_breaker/resume      — 恢复交易
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum

router = APIRouter(prefix="/api/risk/circuit_breaker", tags=["circuit_breaker"])


class CBStatus(str, Enum):
    """熔断器状态枚举"""
    RUNNING = "RUNNING"
    PENDING_CONFIRM = "PENDING_CONFIRM"
    PAUSED = "PAUSED"
    RECOVERING = "RECOVERING"


class CircuitBreakerState:
    """熔断器状态管理，使用本地 JSON 文件持久化"""

    STATE_FILE = "D:\\futures_v6\\data\\circuit_breaker_state.json"

    def __init__(self):
        self.status = CBStatus.RUNNING
        self.trigger_condition = None      # str: 触发条件描述
        self.trigger_time = None           # datetime: 触发时间
        self.confirm_deadline = None       # datetime: 确认截止时间
        self.confirmed_by = None           # str: 确认人
        self.same_direction_pct: float = 0  # float: 同向比例
        self.trigger_detail = {            # dict: 触发详情
            "long_count": 0,
            "short_count": 0,
            "total_count": 0,
        }
        self.history: list = []            # list[dict]: 操作历史

    # ── 序列化 / 反序列化 ──────────────────────────────

    def load(self):
        """从本地 JSON 文件加载状态"""
        import json
        import os

        if not os.path.exists(self.STATE_FILE):
            return

        try:
            with open(self.STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        self.status = CBStatus(data.get("status", "RUNNING"))
        self.trigger_condition = data.get("trigger_condition")
        self.trigger_time = (
            datetime.fromisoformat(data["trigger_time"])
            if data.get("trigger_time")
            else None
        )
        self.confirm_deadline = (
            datetime.fromisoformat(data["confirm_deadline"])
            if data.get("confirm_deadline")
            else None
        )
        self.confirmed_by = data.get("confirmed_by")
        self.same_direction_pct = data.get("same_direction_pct", 0)
        self.trigger_detail = data.get("trigger_detail", {
            "long_count": 0,
            "short_count": 0,
            "total_count": 0,
        })
        self.history = data.get("history", [])

    def save(self):
        """将当前状态持久化到本地 JSON 文件"""
        import json
        import os

        os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)

        payload = {
            "status": self.status.value,
            "trigger_condition": self.trigger_condition,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "confirm_deadline": self.confirm_deadline.isoformat() if self.confirm_deadline else None,
            "confirmed_by": self.confirmed_by,
            "same_direction_pct": self.same_direction_pct,
            "trigger_detail": self.trigger_detail,
            "history": self.history,
        }

        with open(self.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    # ── 状态快照（用于 API 响应）──────────────────────

    def to_dict(self) -> dict:
        """返回当前状态的字典快照"""
        return {
            "status": self.status.value,
            "trigger_condition": self.trigger_condition,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "same_direction_pct": self.same_direction_pct,
            "confirm_deadline": self.confirm_deadline.isoformat() if self.confirm_deadline else None,
            "confirmed_by": self.confirmed_by,
            "trigger_detail": self.trigger_detail,
            "history": self.history,
        }


# ── 全局单例 ───────────────────────────────────────────

cb_state = CircuitBreakerState()
cb_state.load()


# ═══════════════════════════════════════════════════════════
#  Pydantic 请求模型
# ═══════════════════════════════════════════════════════════

class TriggerRequest(BaseModel):
    """触发熔断请求（由监控模块内部调用）"""
    condition: str
    same_direction_pct: float
    long_count: int = 0
    short_count: int = 0
    total_count: int = 0


class ConfirmRequest(BaseModel):
    """确认暂停请求"""
    confirmed_by: str
    notes: str = ""


class DismissRequest(BaseModel):
    """忽略告警请求"""
    confirmed_by: str
    reason: str


class ResumeRequest(BaseModel):
    """恢复交易请求"""
    confirmed_by: str


# ═══════════════════════════════════════════════════════════
#  API Endpoints
# ═══════════════════════════════════════════════════════════

@router.get("")
async def get_status():
    """GET /api/risk/circuit_breaker — 查询当前熔断状态"""
    return cb_state.to_dict()


@router.post("/trigger")
async def trigger(req: TriggerRequest):
    """POST /api/risk/circuit_breaker/trigger — 触发熔断告警

    仅监控模块内部调用。当 >60% 品种同向时触发。
    """
    if cb_state.status != CBStatus.RUNNING:
        return {
            "message": "already in non-running state, trigger ignored",
            "status": cb_state.status.value,
        }

    now = datetime.now()

    cb_state.status = CBStatus.PENDING_CONFIRM
    cb_state.trigger_condition = req.condition
    cb_state.trigger_time = now
    cb_state.confirm_deadline = now + timedelta(minutes=30)
    cb_state.same_direction_pct = req.same_direction_pct
    cb_state.trigger_detail = {
        "long_count": req.long_count,
        "short_count": req.short_count,
        "total_count": req.total_count,
    }
    cb_state.history.append({
        "action": "trigger",
        "status": "PENDING_CONFIRM",
        "time": now.isoformat(),
        "same_direction_pct": req.same_direction_pct,
        "long_count": req.long_count,
        "short_count": req.short_count,
        "total_count": req.total_count,
    })
    cb_state.save()

    # TODO: WebSocket 通知前端（后续补充）

    return {
        "message": "circuit breaker triggered, awaiting confirmation",
        "status": "PENDING_CONFIRM",
        "confirm_deadline": cb_state.confirm_deadline.isoformat(),
    }


@router.post("/confirm_pause")
async def confirm_pause(req: ConfirmRequest):
    """POST /api/risk/circuit_breaker/confirm_pause — 确认暂停交易"""
    if cb_state.status != CBStatus.PENDING_CONFIRM:
        raise HTTPException(status_code=400, detail="not in PENDING_CONFIRM state")

    cb_state.status = CBStatus.PAUSED
    cb_state.confirmed_by = req.confirmed_by
    cb_state.history.append({
        "action": "confirm_pause",
        "status": "PAUSED",
        "confirmed_by": req.confirmed_by,
        "notes": req.notes,
        "time": datetime.now().isoformat(),
    })
    cb_state.save()

    return {"status": "PAUSED", "message": "trading paused"}


@router.post("/dismiss")
async def dismiss(req: DismissRequest):
    """POST /api/risk/circuit_breaker/dismiss — 忽略告警，恢复正常"""
    if cb_state.status not in (CBStatus.PENDING_CONFIRM, CBStatus.RUNNING):
        raise HTTPException(status_code=400, detail="cannot dismiss in current state")

    cb_state.status = CBStatus.RUNNING
    cb_state.history.append({
        "action": "dismiss",
        "status": "RUNNING",
        "confirmed_by": req.confirmed_by,
        "reason": req.reason,
        "time": datetime.now().isoformat(),
    })
    cb_state.save()

    return {"status": "RUNNING", "message": "alert dismissed, trading resumed"}


@router.post("/resume")
async def resume(req: ResumeRequest):
    """POST /api/risk/circuit_breaker/resume — 恢复交易"""
    if cb_state.status != CBStatus.PAUSED:
        raise HTTPException(status_code=400, detail="not in PAUSED state")

    cb_state.status = CBStatus.RECOVERING
    cb_state.history.append({
        "action": "resume",
        "status": "RECOVERING",
        "confirmed_by": req.confirmed_by,
        "time": datetime.now().isoformat(),
    })
    cb_state.save()

    # 简单处理：直接恢复到 RUNNING
    cb_state.status = CBStatus.RUNNING
    cb_state.confirmed_by = None
    cb_state.save()

    return {"status": "RUNNING", "message": "trading resumed"}
