# -*- coding: utf-8 -*-
"""
订单对账 API 路由（D5b）

提供对账引擎状态、差异记录、手动对账触发、差异解决等端点。

端点：
  GET  /api/recon/status         - 对账引擎状态
  GET  /api/recon/discrepancies  - 差异记录列表
  POST /api/recon/reconcile      - 手动触发对账
  POST /api/recon/resolve/{id}   - 标记差异为已解决

@date 2026-05-07
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.reconciliation_engine import get_reconciliation_engine

router = APIRouter(prefix="/api/recon", tags=["recon"])


# ==================== Pydantic 模型 ====================


class ReconcileRequest(BaseModel):
    """手动对账请求"""
    scope: str = "full"  # full | positions | orders


class ResolveRequest(BaseModel):
    """差异解决请求"""
    reason: str


# ==================== 端点实现 ====================


@router.get("/status")
async def recon_status():
    """
    对账引擎状态。

    返回 orders_count, trades_count, positions_count,
    discrepancies (unresolved/WARNING/CRITICAL), engine_status
    """
    engine = get_reconciliation_engine()
    try:
        status = engine.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"code": 0, "message": "success", "data": status}


@router.get("/discrepancies")
async def get_discrepancies(
    unresolved_only: bool = False,
    limit: int = 50,
):
    """
    差异记录列表。

    Query 参数：
      unresolved_only: bool = False   — 只返回未解决的差异
      limit: int = 50                — 最大返回条数

    返回 items[] 和 total（满足条件的总数）
    """
    engine = get_reconciliation_engine()

    try:
        result = engine.get_discrepancies(
            unresolved_only=unresolved_only, limit=limit
        )
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reconcile")
async def trigger_reconcile(req: ReconcileRequest):
    """
    手动触发对账。

    Request body: {"scope": "full"}  — full | positions | orders

    返回 checked_orders, checked_trades, checked_positions,
    new_discrepancies, resolved_discrepancies, duration_ms
    """
    engine = get_reconciliation_engine()

    import time
    start = time.perf_counter()
    try:
        result = engine.reconcile_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    duration_ms = round((time.perf_counter() - start) * 1000)

    result["duration_ms"] = duration_ms
    return {"code": 0, "message": "success", "data": result}


@router.post("/resolve/{id}")
async def resolve_discrepancy(id: int, req: ResolveRequest):
    """
    标记差异为已解决。

    路径参数 id 为 recon_discrepancies 表的 INTEGER 主键（不是 discrepancy_uuid）。
    Request body: {"reason": "解决原因描述"}
    """
    engine = get_reconciliation_engine()

    try:
        success = engine.resolve_discrepancy(id, req.reason)
        if not success:
            raise HTTPException(status_code=404, detail=f"差异记录 id={id} 不存在")

        return {
            "code": 0,
            "message": "success",
            "data": {"id": id, "resolved": True, "resolved_reason": req.reason},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
