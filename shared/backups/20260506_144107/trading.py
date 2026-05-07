from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Literal, ClassVar
from datetime import datetime

from services.vnpy_bridge import get_vnpy_bridge

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
    """下单响应"""
    success: bool
    order_id: Optional[str] = None
    message: str
    timestamp: str


class CancelResponse(BaseModel):
    """撤单响应"""
    success: bool
    message: str
    timestamp: str


@router.post("/order", response_model=OrderResponse)
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
    if not get_vnpy_bridge().is_trading_hours():
        return OrderResponse(
            success=False,
            message="当前不在交易时间内",
            timestamp=datetime.now().isoformat()
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
    
    if vt_orderid:
        return OrderResponse(
            success=True,
            order_id=vt_orderid,
            message=f"订单已发送: {vt_orderid}",
            timestamp=datetime.now().isoformat()
        )
    else:
        return OrderResponse(
            success=False,
            message="订单发送失败，请检查引擎状态和参数",
            timestamp=datetime.now().isoformat()
        )


@router.post("/order/{order_id}/cancel", response_model=CancelResponse)
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
            success=True,
            message=f"撤单成功: {order_id}",
            timestamp=datetime.now().isoformat()
        )
    else:
        return CancelResponse(
            success=False,
            message=f"撤单失败: {order_id}，订单可能已成交或不存在",
            timestamp=datetime.now().isoformat()
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
