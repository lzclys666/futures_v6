# -*- coding: utf-8 -*-

"""

风控相关 API 路由

严格匹配前端 types/risk.ts 类型定义

@author deep

@date 2026-04-29



V6.1 修订：

- /simulate 委托 core/risk_engine.py 的 RiskEngine.check_order()

- Severity 统一为 PASS / WARN / BLOCK（与 risk/rules/risk_rules.yaml 一致）

- Layer 映射：layer1→1/Layer1, layer2→2/Layer2, layer3→3/Layer3

"""

import sys

from pathlib import Path



# 确保 core/risk 在 Python 路径中

_CORE_RISK_DIR = Path(__file__).parent.parent.parent / "core"

if str(_CORE_RISK_DIR) not in sys.path:

    sys.path.insert(0, str(_CORE_RISK_DIR))



from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field

from typing import Literal, Optional

from datetime import datetime



from risk.risk_engine import RiskEngine, OrderRequest, RiskContext, RiskAction
import httpx

from api.alert import get_alert_manager



router = APIRouter(prefix="/api/risk", tags=["risk"])



# 全局风控引擎实例（moderate 画像）

_risk_engine: Optional[RiskEngine] = None



def _get_risk_engine() -> Optional[RiskEngine]:

    """懒加载全局风控引擎"""

    global _risk_engine

    if _risk_engine is None:

        try:

            _risk_engine = RiskEngine(profile='moderate')

        except Exception:

            _risk_engine = None

    return _risk_engine





# ==================== Pydantic 模型（严格匹配前端类型） ====================



# V6.1 统一：Severity 与 YAML 一致 — PASS / WARN / BLOCK

RiskSeverity = Literal['PASS', 'WARN', 'BLOCK']

RiskLayerKey = Literal[1, 2, 3]

RiskRuleId = Literal[

    'R1_SINGLE_SYMBOL', 'R2_DAILY_LOSS', 'R3_PRICE_LIMIT',

    'R4_TOTAL_MARGIN', 'R5_VOLATILITY', 'R6_LIQUIDITY',

    'R7_CONSECUTIVE_LOSS', 'R8_TRADING_HOURS', 'R9_CAPITAL_SUFFICIENCY',

    'R10_MACRO_CIRCUIT_BREAKER', 'R11_DISPOSITION_EFFECT', 'R12_CANCEL_LIMIT',

]



# 规则 ID 映射：前端长名 → YAML 短 ID

RULE_ID_MAP = {

    'R1_SINGLE_SYMBOL': 'R1',

    'R2_DAILY_LOSS': 'R2',

    'R3_PRICE_LIMIT': 'R3',

    'R4_TOTAL_MARGIN': 'R4',

    'R5_VOLATILITY': 'R5',

    'R6_LIQUIDITY': 'R6',

    'R7_CONSECUTIVE_LOSS': 'R7',

    'R8_TRADING_HOURS': 'R8',

    'R9_CAPITAL_SUFFICIENCY': 'R9',

    'R10_MACRO_CIRCUIT_BREAKER': 'R10',

    'R11_DISPOSITION_EFFECT': 'R11',

    'R12_CANCEL_LIMIT': 'R12',

}



# RiskAction → RiskSeverity 映射

ACTION_TO_SEVERITY = {

    RiskAction.PASS: 'PASS',

    RiskAction.WARN: 'WARN',

    RiskAction.BLOCK: 'BLOCK',

}





class RiskRuleStatusItem(BaseModel):

    """前端 RiskRuleStatus - 单条规则状态"""

    ruleId: RiskRuleId

    ruleName: str

    severity: RiskSeverity

    currentValue: float

    threshold: float

    triggered: bool

    message: str

    layer: RiskLayerKey

    updatedAt: str





class RiskStatusResponse(BaseModel):

    """前端 RiskStatusResponse"""

    date: str

    overallStatus: RiskSeverity

    rules: list[RiskRuleStatusItem]

    triggeredCount: int

    circuitBreaker: bool

    updatedAt: str





class RiskRule(BaseModel):

    """前端 RiskRule - 规则配置项"""

    ruleId: RiskRuleId

    ruleName: str

    enabled: bool

    threshold: float

    warnThreshold: Optional[float] = None

    layer: RiskLayerKey

    description: str

    params: Optional[dict] = None





class SimulateRequest(BaseModel):

    """风控预检请求"""

    symbol: str

    direction: Literal['LONG', 'SHORT']

    price: float

    volume: int





class SimulateViolation(BaseModel):

    """风控违规项"""

    ruleId: str

    message: str

    severity: str





class SimulateResponse(BaseModel):

    """风控预检响应"""

    passed: bool = Field(alias="pass")

    violations: list[SimulateViolation]



    class Config:

        populate_by_name = True  # 允许 passed 字段名





class KellyRequest(BaseModel):

    """凯利公式请求"""

    symbol: str

    winRate: float = Field(..., gt=0, lt=1, description="胜率 0-1")

    avgWin: float = Field(..., gt=0, description="平均盈利")

    avgLoss: float = Field(..., gt=0, description="平均亏损")

    capital: float = Field(500000, gt=0, description="资金")

    fraction: Optional[float] = Field(0.5, ge=0, le=1, description="凯利系数")





class KellyResponse(BaseModel):

    """凯利公式响应 - 严格匹配前端字段名"""

    fStar: float

    suggestedPosition: float

    suggestedLots: int

    kellyFraction: float

    interpretation: str





class StressTestRequest(BaseModel):

    """压力测试请求"""

    symbol: str

    scenarios: Optional[list[str]] = None  # 可选，默认跑全部场景





class StressTestResult(BaseModel):

    """单场景压力测试结果"""

    scenarioId: str

    scenarioName: str

    estimatedPnl: float

    estimatedPnlPct: float

    marginChange: float

    riskTriggered: bool

    triggeredRules: list[str]





class StressTestReport(BaseModel):

    """压力测试报告"""

    date: str

    symbol: str

    currentPnl: float

    scenarios: list[StressTestResult]

    worstCase: StressTestResult

    recommendations: list[str]





# ==================== 风控状态 ====================



@router.get("/status")

async def get_risk_status():

    """

    风控状态总览

    返回格式：{code, message, data: RiskStatusResponse}

    """

    try:

        from services.vnpy_bridge import get_vnpy_bridge

        risk_data = get_vnpy_bridge().get_risk_status()

        if isinstance(risk_data, dict):

            # 将 vnpy_bridge 原始格式映射为 RiskStatusResponse

            # 完整格式（已有 overallStatus）直接透传；简化格式（status/active_rules）做转换

            _raw = risk_data

            if "overallStatus" in _raw and "rules" in _raw:

                return {"code": 0, "message": "success", "data": _raw}

            _status = _raw.get("status", "normal")

            _overall = "PASS" if _status == "normal" else "WARN"

            _active: list = _raw.get("active_rules", [])

            _events: list = _raw.get("recent_events", [])

            _RULE_IDS = [

                "R1_SINGLE_SYMBOL", "R2_DAILY_LOSS", "R3_PRICE_LIMIT",

                "R4_TOTAL_MARGIN", "R5_VOLATILITY", "R6_LIQUIDITY",

                "R7_CONSECUTIVE_LOSS", "R8_TRADING_HOURS", "R9_CAPITAL_SUFFICIENCY",

                "R10_MACRO_CIRCUIT_BREAKER", "R11_DISPOSITION_EFFECT", "R12_CANCEL_LIMIT",

            ]

            _RULE_NAMES = {

                "R1_SINGLE_SYMBOL": "R1 单品种持仓限制(动态)",

                "R2_DAILY_LOSS": "R2 单日最大亏损限制",

                "R3_PRICE_LIMIT": "R3 涨跌停限制",

                "R4_TOTAL_MARGIN": "R4 总保证金上限(分时段)",

                "R5_VOLATILITY": "R5 波动率异常过滤",

                "R6_LIQUIDITY": "R6 流动性检查",

                "R7_CONSECUTIVE_LOSS": "R7 连续亏损暂停",

                "R8_TRADING_HOURS": "R8 交易时间检查",

                "R9_CAPITAL_SUFFICIENCY": "R9 资金充足性检查",

                "R10_MACRO_CIRCUIT_BREAKER": "R10 宏观熔断",

                "R11_DISPOSITION_EFFECT": "R11 处置效应监控",

                "R12_CANCEL_LIMIT": "R12 撤单次数限制",

            }

            _RULE_LAYERS = {

                "R1_SINGLE_SYMBOL": 3,

                "R2_DAILY_LOSS": 2,

                "R3_PRICE_LIMIT": 1,

                "R4_TOTAL_MARGIN": 3,

                "R5_VOLATILITY": 1,

                "R6_LIQUIDITY": 1,

                "R7_CONSECUTIVE_LOSS": 2,

                "R8_TRADING_HOURS": 1,

                "R9_CAPITAL_SUFFICIENCY": 3,

                "R10_MACRO_CIRCUIT_BREAKER": 1,

                "R11_DISPOSITION_EFFECT": 2,

                "R12_CANCEL_LIMIT": 2,

            }

            _now = datetime.now().isoformat()

            _rules = []

            for _idx in _active:

                if isinstance(_idx, int) and 1 <= _idx <= len(_RULE_IDS):

                    _rid = _RULE_IDS[_idx - 1]

                    _rules.append({

                        "ruleId": _rid,

                        "ruleName": _RULE_NAMES.get(_rid, _rid),

                        "severity": "WARN",

                        "currentValue": 0.0,

                        "threshold": 0.0,

                        "triggered": True,

                        "message": "",

                        "layer": _RULE_LAYERS.get(_rid, 3),

                        "updatedAt": _now,

                    })

            _cb = any("熔断" in str(e) or "circuit" in str(e).lower() for e in _events)

            return {

                "code": 0,

                "message": "success",

                "data": {

                    "date": datetime.now().strftime("%Y-%m-%d"),

                    "overallStatus": _overall,

                    "rules": _rules,

                    "triggeredCount": len(_active),

                    "circuitBreaker": _cb,

                    "updatedAt": _now,

                }

            }

        # 兼容 list 格式

        return {

            "code": 0,

            "message": "success",

            "data": {

                "date": datetime.now().strftime("%Y-%m-%d"),

                "overallStatus": "PASS",

                "rules": risk_data if isinstance(risk_data, list) else [],

                "triggeredCount": 0,

                "circuitBreaker": False,

                "updatedAt": datetime.now().isoformat()

            }

        }

    except Exception as e:

        return {

            "code": 1,

            "message": str(e),

            "data": None

        }





# ==================== 风控规则 ====================



@router.get("/rules")

async def get_risk_rules():

    """

    风控规则列表

    返回格式：{code, message, data: RiskRule[]}

    """

    try:

        from services.vnpy_bridge import get_vnpy_bridge

        rules_data = get_vnpy_bridge().get_risk_rules() if hasattr(get_vnpy_bridge(), 'get_risk_rules') else []

        return {

            "code": 0,

            "message": "success",

            "data": rules_data

        }

    except Exception as e:

        return {

            "code": 1,

            "message": str(e),

            "data": []

        }





@router.put("/rules/{rule_id}")

async def update_risk_rule(rule_id: str, rule: RiskRule):

    """

    更新单条风控规则配置

    前端调用：PUT /api/risk/rules/{ruleId}

    """

    try:

        # 参数校验

        if rule.ruleId != rule_id:

            raise HTTPException(status_code=400, detail="ruleId 路径参数与请求体不匹配")

        

        # 调用桥接层更新（如果实现）

        from services.vnpy_bridge import get_vnpy_bridge

        if hasattr(get_vnpy_bridge(), 'update_risk_rule'):

            get_vnpy_bridge().update_risk_rule(rule.model_dump())

        

        # 返回更新后的规则

        return {

            "code": 0,

            "message": "success",

            "data": rule.model_dump()

        }

    except HTTPException:

        raise

    except Exception as e:

        return {

            "code": 1,

            "message": str(e),

            "data": None

        }





# ==================== 风控预检 ====================



@router.post("/simulate")

async def simulate_risk(req: SimulateRequest):

    """

    风控预检（下单前）— V6.1 委托 RiskEngine.check_order()

    前端调用：POST /api/risk/simulate

    返回格式：{code, message, data: {pass, violations}}

    """

    violations: list[SimulateViolation] = []



    try:

        from services.vnpy_bridge import get_vnpy_bridge

    except Exception:

        return {

            "code": 0,

            "message": "success",

            "data": {"pass": True, "violations": []}

        }



    engine = _get_risk_engine()

    if engine is None:

        # RiskEngine 初始化失败，降级到 PaperBridge 自身风控

        return await _simulate_fallback(req, get_vnpy_bridge())



    # 1. 构建 OrderRequest

    # 推断交易所：国内期货默认 SHFE，贵金属默认 SHFE

    exchange = _infer_exchange(req.symbol)

    order = OrderRequest(

        symbol=req.symbol,

        exchange=exchange,

        direction=req.direction,

        offset="OPEN",  # 预检默认 OPEN；如需要区分可扩展 SimulateRequest

        price=req.price,

        volume=req.volume,

    )



    # 2. 构建 RiskContext

    account = get_vnpy_bridge().get_account() if hasattr(get_vnpy_bridge(), 'get_account') else None

    positions = get_vnpy_bridge().get_positions() if hasattr(get_vnpy_bridge(), 'get_positions') else []

    # 注入撤单次数到 market_data（供 R12_CancelLimitRule 使用）

    _market_data = {}

    try:

        _bridge = get_vnpy_bridge()

        if hasattr(_bridge, 'get_cancel_count'):

            _cancel_count = _bridge.get_cancel_count(minutes=60)

            _market_data['cancel_count_60m'] = _cancel_count

            _market_data[f'{req.symbol.upper()}_cancel_count_60m'] = _cancel_count

    except Exception:

        pass

    context = RiskContext(

        account=account,

        positions={p.get("symbol", ""): p for p in positions},

        market_data=_market_data,

    )



    # 3. 调用 RiskEngine

    results = engine.check_order(order, context)



    # 4. 转换 RiskResult → SimulateViolation

    for r in results:

        if r.action == RiskAction.PASS:

            continue

        # 短 ID → 前端长名

        long_id = _rule_id_to_long(r.rule_id)

        severity = ACTION_TO_SEVERITY.get(r.action, 'WARN')

        violations.append(SimulateViolation(

            ruleId=long_id,

            message=r.message,

            severity=severity

        ))



    passed = len(violations) == 0

    # Alert integration: trigger alerts on WARN/BLOCK violations
    if not passed:
        try:
            mgr = get_alert_manager()
            for v in violations:
                level = "CRITICAL" if v.severity == "BLOCK" else "WARNING"
                mgr.add_alert(
                    level=level,
                    category=f"risk_{v.severity.lower()}",
                    message=f"[{v.ruleId}] {v.message}",
                    details={"symbol": req.symbol, "direction": req.direction, "ruleId": v.ruleId}
                )
        except Exception:
            pass  # alert failure must not block risk check

    return {
        "code": 0,
        "message": "success",
        "data": {
            "pass": passed,
            "violations": [v.model_dump() for v in violations]
        }
    }





@router.post("/precheck")
async def risk_precheck(req: SimulateRequest):
    """
    风控预检（轻量级） — 前端下单前调用
    优先 RiskEngine.check_order()，不可用时降级到 _simulate_fallback
    前端调用：POST /api/risk/precheck
    返回格式：{code, message, data: {pass, violations}}
    """
    try:
        from services.vnpy_bridge import get_vnpy_bridge
    except Exception:
        return {
            "code": 0,
            "message": "success",
            "data": {"pass": True, "violations": []}
        }

    engine = _get_risk_engine()
    if engine is None:
        return await _simulate_fallback(req, get_vnpy_bridge())

    # 构建 OrderRequest
    exchange = _infer_exchange(req.symbol)
    order = OrderRequest(
        symbol=req.symbol,
        exchange=exchange,
        direction=req.direction,
        offset="OPEN",
        price=req.price,
        volume=req.volume,
    )

    # 构建 RiskContext
    account = get_vnpy_bridge().get_account() if hasattr(get_vnpy_bridge(), 'get_account') else None
    positions = get_vnpy_bridge().get_positions() if hasattr(get_vnpy_bridge(), 'get_positions') else []

    # 注入撤单次数到 market_data（供 R12_CancelLimitRule 使用）
    _market_data = {}
    try:
        _bridge = get_vnpy_bridge()
        if hasattr(_bridge, 'get_cancel_count'):
            _cancel_count = _bridge.get_cancel_count(minutes=60)
            _market_data['cancel_count_60m'] = _cancel_count
            _market_data[f'{req.symbol.upper()}_cancel_count_60m'] = _cancel_count
    except Exception:
        pass

    context = RiskContext(
        account=account,
        positions={p.get("symbol", ""): p for p in positions},
        market_data=_market_data,
    )

    # 调用 RiskEngine
    violations: list[SimulateViolation] = []
    results = engine.check_order(order, context)

    for r in results:
        if r.action == RiskAction.PASS:
            continue
        long_id = _rule_id_to_long(r.rule_id)
        severity = ACTION_TO_SEVERITY.get(r.action, 'WARN')
        violations.append(SimulateViolation(
            ruleId=long_id,
            message=r.message,
            severity=severity
        ))

    passed = len(violations) == 0
    return {
        "code": 0,
        "message": "success",
        "data": {
            "pass": passed,
            "violations": [v.model_dump(by_alias=True) for v in violations]
        }
    }


def _infer_exchange(symbol: str) -> str:

    """从合约代码推断交易所"""

    s = symbol.upper()

    # 上期所

    if any(s.startswith(p) for p in ['CU', 'AL', 'ZN', 'PB', 'NI', 'SN', 'AU', 'AG', 'RB', 'HC', 'WR', 'BU', 'RU', 'FU']):

        return "SHFE"

    # 大商所

    if any(s.startswith(p) for p in ['I', 'J', 'JM', 'M', 'Y', 'A', 'B', 'P', 'C', 'CS', 'L', 'V', 'PP', 'EG', 'EB', 'PG', 'LH']):

        return "DCE"

    # 郑商所

    if any(s.startswith(p) for p in ['SR', 'CF', 'RM', 'OI', 'CY', 'AP', 'CJ', 'UR', 'SA', 'FG', 'TA', 'MA', 'ZC', 'SF', 'SM', 'PK', 'LC']):

        return "CZCE"

    # 中金所

    if any(s.startswith(p) for p in ['IF', 'IC', 'IH', 'IM', 'TF', 'TS', 'T', 'TL']):

        return "CFFEX"

    # 能源中心

    if any(s.startswith(p) for p in ['SC', 'NR', 'LU', 'EC', 'BC']):

        return "INE"

    # 广期所

    if any(s.startswith(p) for p in ['SI']):

        return "GFEX"

    return "SHFE"





def _rule_id_to_long(short_id: str) -> str:

    """短 ID → 前端长名（反向查找 RULE_ID_MAP）"""

    for long_name, sid in RULE_ID_MAP.items():

        if sid == short_id:

            return long_name

    return short_id





async def _simulate_fallback(req: SimulateRequest, bridge) -> dict:

    """

    RiskEngine 不可用时的降级检查（保留核心 4 条规则）

    """

    violations: list[SimulateViolation] = []



    # R8：交易时段

    if hasattr(get_vnpy_bridge(), 'is_trading_hours') and not bridge.is_trading_hours():

        violations.append(SimulateViolation(

            ruleId="R8_TRADING_HOURS", message="当前非交易时段", severity="BLOCK"

        ))



    # R9：资金充足性

    account = bridge.get_account() if hasattr(get_vnpy_bridge(), 'get_account') else None

    if account:

        available = account.get("available", 0)

        required_margin = req.price * req.volume * 10 * 0.1

        if available < required_margin:

            violations.append(SimulateViolation(

                ruleId="R9_CAPITAL_SUFFICIENCY",

                message=f"可用资金不足：需要 {required_margin:.2f}，可用 {available:.2f}",

                severity="BLOCK"

            ))



    # R1：单品种持仓上限

    positions = get_vnpy_bridge().get_positions() if hasattr(get_vnpy_bridge(), 'get_positions') else []

    current_vol = sum(

        p.get("volume", 0)

        for p in positions

        if req.symbol.upper() in p.get("symbol", "").upper()

        and p.get("direction", "") == req.direction.upper()

    )

    if current_vol + req.volume > 20:

        violations.append(SimulateViolation(

            ruleId="R1_SINGLE_SYMBOL",

            message=f"单品种持仓超限：当前 {current_vol} 手 + 委托 {req.volume} 手 > 20 手",

            severity="BLOCK"

        ))



    # R10：宏观熔断（走标准 API）

    try:

        import re

        main_symbol = re.sub(r'\d+$', '', req.symbol.upper())

        async with httpx.AsyncClient(timeout=3.0) as client:

            resp = await client.get(f"http://localhost:8000/api/signal/{main_symbol}")

            if resp.status_code == 200:

                data = resp.json()

                signal_data = data.get("data", {})

                score = signal_data.get("compositeScore", 0)

                if req.direction.upper() == "LONG" and score < -0.5:

                    violations.append(SimulateViolation(

                        ruleId="R10_MACRO_CIRCUIT_BREAKER",

                        message=f"宏观打分过低 ({score:.2f})，禁止做多",

                        severity="BLOCK"

                    ))

                if req.direction.upper() == "SHORT" and score > 0.7:

                    violations.append(SimulateViolation(

                        ruleId="R10_MACRO_CIRCUIT_BREAKER",

                        message=f"宏观打分过高 ({score:.2f})，禁止做空",

                        severity="BLOCK"

                    ))

    except Exception:

        pass



    # R12：撤单次数限制

    try:

        # 获取最近60分钟内的撤单次数

        cancel_count = 0

        if hasattr(bridge, 'get_cancel_count'):

            cancel_count = bridge.get_cancel_count(minutes=60)



        # 根据风控画像获取阈值（默认中等=10）

        max_cancels = 10  # 默认中等画像



        if cancel_count >= max_cancels:

            violations.append(SimulateViolation(

                ruleId="R12_CANCEL_LIMIT",

                message=f"撤单次数过多：60分钟内 {cancel_count} 次 ≥ {max_cancels} 次",

                severity="BLOCK"

            ))

        elif cancel_count >= int(max_cancels * 0.8):

            violations.append(SimulateViolation(

                ruleId="R12_CANCEL_LIMIT",

                message=f"撤单次数预警：60分钟内 {cancel_count} 次，接近阈值 {max_cancels} 次",

                severity="WARN"

            ))

    except Exception:

        pass



    passed = len(violations) == 0

    return {

        "code": 0,

        "message": "success",

        "data": {

            "pass": passed,

            "violations": [v.model_dump(by_alias=True) for v in violations]

        }

    }





# ==================== 凯利公式 ====================



@router.post("/kelly")

async def calc_kelly(req: KellyRequest):

    """

    凯利公式计算

    前端调用：POST /api/risk/kelly

    返回格式：{code, message, data: KellyResponse}

    """

    p = req.winRate

    q = 1 - p

    b = req.avgWin / req.avgLoss  # 盈亏比

    

    # 凯利公式：kelly = (p * B - q) / B

    kelly = (p * b - q) / b

    kelly = max(0, min(kelly, 1))  # 限制在 [0, 1]

    

    # 应用凯利系数

    kelly_fraction = req.fraction if req.fraction else 0.5

    adjusted_kelly = kelly * kelly_fraction

    

    # 建议仓位

    suggested_position = adjusted_kelly

    # 简化计算：假设每手合约价值 = 10000

    contract_value = 10000

    suggested_lots = max(1, int(req.capital * adjusted_kelly / contract_value))

    

    # 解释文本

    if adjusted_kelly < 0.1:

        interpretation = f"建议仓位较低（{adjusted_kelly*100:.1f}%），风险可控"

    elif adjusted_kelly < 0.25:

        interpretation = f"建议仓位适中（{adjusted_kelly*100:.1f}%），注意风险管理"

    else:

        interpretation = f"建议仓位较高（{adjusted_kelly*100:.1f}%），建议降低仓位或使用更保守的凯利系数"

    

    return {

        "code": 0,

        "message": "success",

        "data": {

            "fStar": round(kelly, 4),

            "suggestedPosition": round(suggested_position, 4),

            "suggestedLots": suggested_lots,

            "kellyFraction": kelly_fraction,

            "interpretation": interpretation

        }

    }





# ==================== 压力测试 ====================



STRESS_SCENARIOS = [

    {"id": "s1", "name": "黑天鹅事件", "priceChangePct": -0.082, "volMultiplier": 2.0},

    {"id": "s2", "name": "极端波动", "priceChangePct": -0.055, "volMultiplier": 1.5},

    {"id": "s3", "name": "流动性枯竭", "priceChangePct": -0.15, "volMultiplier": 1.0},

    {"id": "s4", "name": "连续亏损", "priceChangePct": -0.016, "volMultiplier": 1.2},

]





@router.post("/stress-test")

async def run_stress_test(req: StressTestRequest):

    """

    压力测试

    前端调用：POST /api/risk/stress-test

    返回格式：{code, message, data: StressTestReport}

    """

    try:

        from services.vnpy_bridge import get_vnpy_bridge

        

        # 获取当前持仓 PnL

        positions = get_vnpy_bridge().get_positions() if hasattr(get_vnpy_bridge(), 'get_positions') else []

        current_pnl = sum(p.get("pnl", 0) for p in positions)

        

        # 计算总敞口

        total_exposure = sum(

            p.get("price", 0) * p.get("volume", 0) * 10

            for p in positions

            if req.symbol.upper() in p.get("symbol", "").upper()

        )

        abs_exposure = abs(total_exposure) if total_exposure != 0 else 100000  # 默认10万

        

        # 选择场景

        scenarios_to_run = STRESS_SCENARIOS

        if req.scenarios:

            scenarios_to_run = [s for s in STRESS_SCENARIOS if s["id"] in req.scenarios]

        

        # 计算每个场景的影响

        results: list[StressTestResult] = []

        for scenario in scenarios_to_run:

            estimated_pnl = abs_exposure * scenario["priceChangePct"]

            estimated_pnl_pct = scenario["priceChangePct"]

            margin_change = abs_exposure * 0.1 * (scenario["volMultiplier"] - 1)

            

            # 判断是否触发风控

            risk_triggered = abs(estimated_pnl_pct) > 0.05

            triggered_rules = []

            if abs(estimated_pnl_pct) > 0.05:

                triggered_rules.append("R5_VOLATILITY")

            if abs(estimated_pnl_pct) > 0.10:

                triggered_rules.append("R2_DAILY_LOSS")

            if margin_change < -5000:

                triggered_rules.append("R9_CAPITAL_SUFFICIENCY")

            

            results.append(StressTestResult(

                scenarioId=scenario["id"],

                scenarioName=scenario["name"],

                estimatedPnl=round(estimated_pnl, 2),

                estimatedPnlPct=round(estimated_pnl_pct, 4),

                marginChange=round(margin_change, 2),

                riskTriggered=risk_triggered,

                triggeredRules=triggered_rules

            ))

        

        # 找出最坏情况

        worst_case = min(results, key=lambda r: r.estimatedPnl)

        

        # 生成建议

        recommendations = []

        if worst_case.estimatedPnlPct < -0.05:

            recommendations.append("建议降低仓位至 50% 以下")

        if any(r.riskTriggered for r in results):

            recommendations.append("启用对冲策略")

        if worst_case.estimatedPnlPct < -0.10:

            recommendations.append("考虑止损离场")

        if not recommendations:

            recommendations.append("当前仓位风险可控")

        

        return {

            "code": 0,

            "message": "success",

            "data": {

                "date": datetime.now().strftime("%Y-%m-%d"),

                "symbol": req.symbol,

                "currentPnl": round(current_pnl, 2),

                "scenarios": [r.model_dump() for r in results],

                "worstCase": worst_case.model_dump(),

                "recommendations": recommendations

            }

        }

    except Exception as e:

        return {

            "code": 1,

            "message": str(e),

            "data": None

        }


# ==================== WebSocket 风控推送 ====================

import asyncio
import json
import logging as _risk_logging
from typing import Any, Set

_risk_logger = _risk_logging.getLogger("risk_ws")


class RiskConnectionManager:
    """管理 /ws/risk 的 WebSocket 连接"""

    def __init__(self) -> None:
        self._connections: Set[Any] = set()

    @property
    def count(self) -> int:
        return len(self._connections)

    def add(self, ws: Any) -> None:
        self._connections.add(ws)
        _risk_logger.info(f"Risk WS client +1, total={self.count}")

    def remove(self, ws: Any) -> None:
        self._connections.discard(ws)
        _risk_logger.info(f"Risk WS client -1, total={self.count}")

    def get_all(self) -> list:
        return list(self._connections)

    async def broadcast(self, message: dict) -> None:
        payload = json.dumps(message, ensure_ascii=False)
        stale: list = []
        for ws in self.get_all():
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.remove(ws)


_risk_ws_manager = RiskConnectionManager()


def _get_risk_status_data() -> dict:
    """获取风控状态数据（复用 /api/risk/status 逻辑）"""
    try:
        from services.vnpy_bridge import get_vnpy_bridge
        risk_data = get_vnpy_bridge().get_risk_status()
        if isinstance(risk_data, dict) and "overallStatus" in risk_data and "rules" in risk_data:
            return risk_data
        _status = risk_data.get("status", "normal") if isinstance(risk_data, dict) else "normal"
        _overall = "PASS" if _status == "normal" else "WARN"
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "overallStatus": _overall,
            "rules": risk_data.get("active_rules", []) if isinstance(risk_data, dict) else [],
            "triggeredCount": 0,
            "circuitBreaker": False,
            "updatedAt": datetime.now().isoformat(),
        }
    except Exception:
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "overallStatus": "PASS",
            "rules": [],
            "triggeredCount": 0,
            "circuitBreaker": False,
            "updatedAt": datetime.now().isoformat(),
        }



async def _risk_broadcast_loop() -> None:
    """后台任务：每 5 秒向所有 /ws/risk 客户端广播风控状态"""
    while True:
        try:
            if _risk_ws_manager.count > 0:
                status_data = _get_risk_status_data()
                await _risk_ws_manager.broadcast({
                    "type": "risk_status_update",
                    "data": status_data,
                })
        except Exception as e:
            _risk_logger.error(f"Risk broadcast error: {e}")
        await asyncio.sleep(5)


# ==================== Alert API ====================

@router.get("/alerts")
async def get_alerts(
    level: Optional[str] = None,
    limit: int = 100,
    since: Optional[str] = None,
):
    """
    Get recent alerts.

    Query params:
        level:  INFO | WARNING | CRITICAL (optional filter)
        limit:  max items (default 100)
        since:  ISO timestamp — only alerts after this time

    Returns: {"code": 0, "message": "success", "data": {"alerts": [...], "total": N}}
    """
    try:
        mgr = get_alert_manager()
        result = mgr.get_alerts(level=level, limit=limit, since=since)
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        return {"code": 1, "message": str(e), "data": {"alerts": [], "total": 0}}


@router.get("/alerts/stats")
async def get_alert_stats():
    """
    Get alert statistics.

    Returns: {"code": 0, "message": "success", "data": {
        "total": N, "critical": N, "warning": N, "info": N,
        "last_critical": "..." or null
    }}
    """
    try:
        mgr = get_alert_manager()
        result = mgr.get_stats()
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        return {"code": 1, "message": str(e), "data": {
            "total": 0, "critical": 0, "warning": 0, "info": 0, "last_critical": None
        }}
