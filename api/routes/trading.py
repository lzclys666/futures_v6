from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Literal, ClassVar
from datetime import datetime

from services.vnpy_bridge import get_vnpy_bridge
from services.reconciliation_engine import get_reconciliation_engine

router = APIRouter(prefix="/api/trading", tags=["trading"])


# ==================== 统一响应辅助 ====================

def _wrap(data=None, message: str = "success", code: int = 0):
    """统一 API 响应格式：{code, message, data}"""
    return {"code": code, "message": message, "data": data}


class OrderRequest(BaseModel):
    """下单请求"""
    symbol: str = ""               # 品种代码，如 "CU" / "AU" / "RU"（可选）
    vt_symbol: str = ""           # 完整合约代码，如 "RU2505.SHFE"（优先使用）
    direction: Literal["LONG", "SHORT"]
    offset: Literal["OPEN", "CLOSE", "CLOSETODAY", "CLOSEYESTERDAY"] = "OPEN"  # 默认开仓
    volume: int
    price: float
    order_type: Literal["LIMIT", "MARKET"] = "LIMIT"
    
    # 品种到交易所的映射（主力合约）
    SYMBOL_MAP: ClassVar[dict[str, str]] = {
        "CU": "SHFE.CU2505",
        "AU": "SHFE.AU2506",
        "AG": "SHFE.AG2506",
        "ZN": "SHFE.ZN2505",
        "AL": "SHFE.AL2505",
        "RB": "SHFE.RB2505",
        "RU": "SHFE.RU2505",
        "NI": "SHFE.NI2505",
        "SS": "SHFE.SS2505",
        "HC": "SHFE.HC2505",
        "I": "DCE.I2505",
        "J": "DCE.J2505",
        "JM": "DCE.JM2505",
        "PP": "DCE.PP2505",
        "L": "DCE.L2505",
        "V": "DCE.V2505",
        "EG": "DCE.EG2505",
        "EB": "DCE.EB2505",
        "P": "DCE.P2505",
        "M": "DCE.M2505",
        "Y": "DCE.Y2505",
        "A": "DCE.A2505",
        "C": "DCE.C2505",
        "CS": "DCE.CS2505",
        "TA": "ZCE.TA505",
        "CF": "ZCE.CF505",
        "SR": "ZCE.SR505",
        "FG": "ZCE.FG505",
        "MA": "ZCE.MA505",
        "OI": "ZCE.OI505",
        "RM": "ZCE.RM505",
        "AP": "ZCE.AP505",
        "SC": "INE.SC2506",
        "NR": "INE.NR2505",
        "LU": "INE.LU2505",
        "BC": "INE.BC2505",
    }
    
    def get_symbol(self) -> str:
        """获取实际使用的完整合约代码"""
        # 优先使用显式传入的 vt_symbol（如 "RU2505.SHFE"）
        if self.vt_symbol:
            # 检查是否已经是完整格式（包含.）
            if '.' in self.vt_symbol:
                # 前端发送格式: "RU2505.SHFE"，需转换为 "SHFE.RU2505"
                parts = self.vt_symbol.split('.')
                if len(parts) == 2:
                    return f"{parts[1]}.{parts[0]}"
            return self.vt_symbol
        
        # 使用 symbol 自动补全
        if self.symbol:
            symbol_upper = self.symbol.upper()
            if symbol_upper in self.SYMBOL_MAP:
                return self.SYMBOL_MAP[symbol_upper]
            return f"SHFE.{symbol_upper}2505"
        
        # 默认返回 RU
        return "SHFE.RU2505"


class OrderResponse(BaseModel):
    """下单响应 — 对齐前端 types/trading.ts OrderResponse"""
    orderId: str = Field("", alias="orderId")
    symbol: str = ""
    direction: str = ""
    price: float = 0.0
    volume: int = 0
    tradedVolume: int = 0
    status: str = "PENDING"
    createdAt: str = ""
    updatedAt: str = ""
    message: Optional[str] = None
    success: bool = True

    class Config:
        populate_by_name = True


class CancelResponse(BaseModel):
    """撤单响应 — 对齐前端 types/trading.ts CancelOrderResponse"""
    orderId: str = Field("", alias="orderId")
    success: bool = True
    message: Optional[str] = None

    class Config:
        populate_by_name = True


@router.post("/order", response_model=OrderResponse, response_model_by_alias=True)
async def create_order(request: OrderRequest):
    """
    发送委托订单
    
    请求示例:
    ```json
    {
        "symbol": "RU2505.SHFE",
        "direction": "LONG",
        "offset": "OPEN",
        "volume": 1,
        "price": 15000.0,
        "order_type": "LIMIT"
    }
    ```
    """
    # 检查引擎状态
    if not get_vnpy_bridge().status.value == "running":
        raise HTTPException(
            status_code=503,
            detail="交易引擎未启动，请先启动VNpy引擎"
        )
    
    # 检查交易时间
    now_iso = datetime.now().isoformat()
    if not get_vnpy_bridge().is_trading_hours():
        return OrderResponse(
            orderId="",
            symbol="",
            direction="",
            price=0.0,
            volume=0,
            tradedVolume=0,
            status="REJECTED",
            createdAt=now_iso,
            updatedAt=now_iso,
            message="当前不在交易时间内",
            success=False,
        )
    
    # 发送订单
    vt_symbol = request.get_symbol()
    vt_orderid = get_vnpy_bridge().send_order(
        vt_symbol=vt_symbol,
        direction=request.direction,
        offset=request.offset,
        price=request.price,
        volume=request.volume
    )
    
    now_iso = datetime.now().isoformat()
    if vt_orderid:
        # 解析 vt_orderid 提取 symbol 和 direction
        # vt_orderid 格式: "EXCHANGE.SYMBOL-DIRECTION-COUNTER" (e.g. "SHFE.RU2505-LONG-abc12345")
        parsed_symbol = ""
        parsed_direction = ""
        try:
            parts = vt_orderid.split("-")
            if len(parts) >= 2:
                parsed_symbol = parts[0]  # e.g. "SHFE.RU2505"
                parsed_direction = parts[1]  # e.g. "LONG"
        except Exception:
            pass

        # 集成对账引擎：record_order
        try:
            engine = get_reconciliation_engine()
            order_uuid = engine.record_order({
                "symbol": parsed_symbol or vt_symbol,
                "exchange": "",  # 从 parsed_symbol 提取或留空
                "direction": parsed_direction or request.direction,
                "offset": request.offset,
                "price": request.price,
                "volume": request.volume,
                "vt_orderid": vt_orderid,
                "source": "api",
            })
            # 注册 vt_orderid → order_uuid 映射，供成交回调时查找
            _bridge = get_vnpy_bridge()
            if _bridge is not None and hasattr(_bridge, 'set_order_uuid_mapping'):
                _bridge.set_order_uuid_mapping(vt_orderid, order_uuid)
        except Exception as e:
            # 对账失败不应阻塞交易主流程，只记录警告
            import logging
            logging.getLogger("trading").warning(f"[Reconciliation] record_order failed: {e}")

        return OrderResponse(
            orderId=vt_orderid,
            symbol=parsed_symbol or vt_symbol,
            direction=parsed_direction or request.direction,
            price=request.price,
            volume=request.volume,
            tradedVolume=0,
            status="NOT_TRADED",
            createdAt=now_iso,
            updatedAt=now_iso,
            message=f"订单已发送: {vt_orderid}",
            success=True,
        )
    else:
        return OrderResponse(
            orderId="",
            symbol=vt_symbol,
            direction=request.direction,
            price=request.price,
            volume=request.volume,
            tradedVolume=0,
            status="REJECTED",
            createdAt=now_iso,
            updatedAt=now_iso,
            message="订单发送失败，请检查引擎状态和参数",
            success=False,
        )


@router.post("/order/{order_id}/cancel", response_model=CancelResponse, response_model_by_alias=True)
async def cancel_order(order_id: str):
    """
    撤销委托订单
    
    路径参数:
    - order_id: 委托编号（如 "PaperAccount.12345"）
    """
    # 检查引擎状态
    if not get_vnpy_bridge().status.value == "running":
        raise HTTPException(
            status_code=503,
            detail="交易引擎未启动"
        )
    
    # 执行撤单
    success = get_vnpy_bridge().cancel_order(vt_orderid=order_id)
    
    if success:
        return CancelResponse(
            orderId=order_id,
            success=True,
            message=f"撤单成功: {order_id}",
        )
    else:
        return CancelResponse(
            orderId=order_id,
            success=False,
            message=f"撤单失败: {order_id}，订单可能已成交或不存在",
        )


@router.get("/positions")
async def get_positions():
    """获取持仓列表"""
    if not get_vnpy_bridge().status.value == "running":
        return {"status": "engine_not_running", "positions": []}

    positions = get_vnpy_bridge().get_positions()
    return _wrap({"count": len(positions), "positions": positions})


@router.get("/account")
async def get_account():
    """获取账户信息"""
    if not get_vnpy_bridge().status.value == "running":
        return _wrap(None, message="engine_not_running")

    account = get_vnpy_bridge().get_account()
    return _wrap({"account": account})


@router.get("/portfolio")
async def get_portfolio():
    """
    获取聚合组合数据（账户统计 + 持仓列表）
    用于前端 PortfolioData，支持 PositionBoard 完整展示
    """
    if not get_vnpy_bridge().status.value == "running":
        return _wrap(None, message="engine_not_running")

    portfolio = get_vnpy_bridge().get_portfolio()
    return _wrap({"portfolio": portfolio})


@router.get("/orders")
async def get_orders():
    """获取订单列表"""
    if not get_vnpy_bridge().status.value == "running":
        return _wrap(None, message="engine_not_running")

    orders = get_vnpy_bridge().get_orders()
    return _wrap({"count": len(orders), "orders": orders})


@router.get("/trades")
async def get_trades():
    """获取成交列表"""
    if not get_vnpy_bridge().status.value == "running":
        return _wrap(None, message="engine_not_running")

    trades = get_vnpy_bridge().get_trades()
    return _wrap({"count": len(trades), "trades": trades})
