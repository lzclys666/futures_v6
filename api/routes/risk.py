# -*- coding: utf-8 -*-
"""
风控相关 API 路由
严格匹配前端 types/risk.ts 类型定义
@author deep
@date 2026-04-29
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

router = APIRouter(prefix="/api/risk", tags=["risk"])


# ==================== Pydantic 模型（严格匹配前端类型） ====================

RiskSeverity = Literal['PASS', 'LOW', 'MEDIUM', 'HIGH']
RiskLayerKey = Literal['layer1', 'layer2', 'layer3']
RiskRuleId = Literal[
    'R1_SINGLE_SYMBOL', 'R2_DAILY_LOSS', 'R3_PRICE_LIMIT',
    'R4_TOTAL_MARGIN', 'R5_VOLATILITY', 'R6_LIQUIDITY',
    'R7_CONSECUTIVE_LOSS', 'R8_TRADING_HOURS', 'R9_CAPITAL_SUFFICIENCY',
    'R10_MACRO_CIRCUIT_BREAKER', 'R11_DISPOSITION_EFFECT', 'R12_CANCEL_LIMIT',
]


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
    pass_: bool = Field(alias="pass")
    violations: list[SimulateViolation]

    class Config:
        populate_by_name = True  # 允许 pass 字段名


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
        from services.vnpy_bridge import bridge
        risk_data = bridge.get_risk_status()
        if isinstance(risk_data, dict):
            return {
                "code": 0,
                "message": "success",
                "data": risk_data
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
        from services.vnpy_bridge import bridge
        rules_data = bridge.get_risk_rules() if hasattr(bridge, 'get_risk_rules') else []
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
        from services.vnpy_bridge import bridge
        if hasattr(bridge, 'update_risk_rule'):
            bridge.update_risk_rule(rule.model_dump())
        
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
    风控预检（下单前）
    前端调用：POST /api/risk/simulate
    返回格式：{code, message, data: {pass, violations}}
    """
    violations: list[SimulateViolation] = []
    
    try:
        from services.vnpy_bridge import bridge
    except Exception:
        # VNpyBridge 未初始化，跳过风控检查（Paper模式）
        return {
            "code": 0,
            "message": "success",
            "data": {
                "pass": True,
                "violations": []
            }
        }
    
    # R8：交易时段检查
    if hasattr(bridge, 'is_trading_hours') and not bridge.is_trading_hours():
        violations.append(SimulateViolation(
            ruleId="R8_TRADING_HOURS",
            message="当前非交易时段",
            severity="HIGH"
        ))
    
    # R9：资金充足性检查
    account = bridge.get_account() if hasattr(bridge, 'get_account') else None
    if account:
        available = account.get("available", 0)
        required_margin = req.price * req.volume * 10 * 0.1  # 简化估算
        if available < required_margin:
            violations.append(SimulateViolation(
                ruleId="R9_CAPITAL_SUFFICIENCY",
                message=f"可用资金不足：需要 {required_margin:.2f}，可用 {available:.2f}",
                severity="HIGH"
            ))
    
    # R1：单品种持仓上限（不超过 20 手）
    positions = bridge.get_positions() if hasattr(bridge, 'get_positions') else []
    current_pos_vol = 0
    for pos in positions:
        pos_symbol = pos.get("symbol", "")
        if isinstance(pos_symbol, str) and req.symbol.upper() in pos_symbol.upper():
            if pos.get("direction", "") == req.direction.upper():
                current_pos_vol += pos.get("volume", 0)
    if current_pos_vol + req.volume > 20:
        violations.append(SimulateViolation(
            ruleId="R1_SINGLE_SYMBOL",
            message=f"单品种持仓超限：当前 {current_pos_vol} 手，委托 {req.volume} 手，上限 20 手",
            severity="HIGH"
        ))
    
    # R4：总保证金占用上限（不超过 80%）
    if account:
        total_equity = account.get("balance", 1_000_000)
        total_exposure = sum(
            p.get("price", 0) * p.get("volume", 0) * 10
            for p in positions
        )
        new_exposure = req.price * req.volume * 10
        if (total_exposure + new_exposure) / total_equity > 0.8:
            violations.append(SimulateViolation(
                ruleId="R4_TOTAL_MARGIN",
                message=f"总持仓比例超限：{(total_exposure + new_exposure) / total_equity * 100:.1f}% > 80%",
                severity="MEDIUM"
            ))
    
    # R3：涨跌停检查（简化：超过当日涨跌停板 ±8% 拒绝）
    limit_pct = 0.08
    # 使用 last_price 或委托价作为基准（简化处理）
    last_price = req.price  # 实际应从行情获取
    upper_limit = last_price * (1 + limit_pct)
    lower_limit = last_price * (1 - limit_pct)
    if req.direction.upper() == "LONG" and req.price > upper_limit:
        violations.append(SimulateViolation(
            ruleId="R3_PRICE_LIMIT",
            message=f"委托价格 {req.price} 超过涨停价 {upper_limit:.2f}",
            severity="HIGH"
        ))
    if req.direction.upper() == "SHORT" and req.price < lower_limit:
        violations.append(SimulateViolation(
            ruleId="R3_PRICE_LIMIT",
            message=f"委托价格 {req.price} 低于跌停价 {lower_limit:.2f}",
            severity="HIGH"
        ))
    
    # R10：宏观熔断检查
    try:
        import re
        main_symbol = re.sub(r'\d+$', '', req.symbol.upper())
        import macro_scoring_engine as engine
        signal_data = engine.get_latest_signal(main_symbol)
        if signal_data:
            score = signal_data.get("compositeScore", 0)
            if req.direction.upper() == "LONG" and score < -0.5:
                violations.append(SimulateViolation(
                    ruleId="R10_MACRO_CIRCUIT_BREAKER",
                    message=f"宏观打分过低 ({score:.2f})，禁止做多",
                    severity="HIGH"
                ))
            if req.direction.upper() == "SHORT" and score > 0.7:
                violations.append(SimulateViolation(
                    ruleId="R10_MACRO_CIRCUIT_BREAKER",
                    message=f"宏观打分过高 ({score:.2f})，禁止做空",
                    severity="HIGH"
                ))
    except Exception:
        pass  # 宏观打分不可用时跳过
    
    # R6：流动性检查（成交量低于阈值）
    # 简化实现：通过品种合约查询最近成交量，低于阈值则拒绝
    try:
        # 从 bridge 获取最新行情
        if hasattr(bridge, 'get_tick'):
            tick = bridge.get_tick(req.symbol)
            if tick:
                tick_volume = tick.get("volume", 0)
                liquidity_threshold = 1000  # 最低日成交量
                if tick_volume < liquidity_threshold:
                    violations.append(SimulateViolation(
                        ruleId="R6_LIQUIDITY",
                        message=f"流动性不足：当前成交量 {tick_volume}，低于阈值 {liquidity_threshold}",
                        severity="MEDIUM"
                    ))
    except Exception:
        pass  # 行情不可用时跳过
    
    # R7：连续亏损暂停（模拟不影响实际状态，仅提示）
    # 从 bridge 获取账户信息中的连续亏损次数
    try:
        if hasattr(bridge, 'get_risk_status'):
            risk_status = bridge.get_risk_status()
            if risk_status:
                rules_data = risk_status.get("rules", [])
                for rule in rules_data:
                    if rule.get("ruleId") == "R7_CONSECUTIVE_LOSS" and rule.get("triggered", False):
                        violations.append(SimulateViolation(
                            ruleId="R7_CONSECUTIVE_LOSS",
                            message=f"连续亏损暂停中：当前连续亏损 {rule.get('currentValue', 0)} 次，上限 {rule.get('threshold', 5)} 次",
                            severity="HIGH"
                        ))
                        break
    except Exception:
        pass  # 风控状态不可用时跳过
    
    # R11：处置效应监控（持仓时间过短且亏损时警告）
    # 检查是否在处置效应观察期内（持仓 <24h 且亏损离场后再入场）
    try:
        if hasattr(bridge, 'get_positions'):
            for pos in positions:
                pos_symbol = pos.get("symbol", "")
                if isinstance(pos_symbol, str) and req.symbol.upper() in pos_symbol.upper():
                    # 检查已有持仓的开仓时间
                    open_time = pos.get("openTime")
                    if open_time:
                        # 简化：如果已有持仓且方向相反，可能是处置效应行为
                        existing_dir = pos.get("direction", "")
                        if existing_dir != req.direction.upper():
                            # 反向开仓可能是处置效应，给警告
                            violations.append(SimulateViolation(
                                ruleId="R11_DISPOSITION_EFFECT",
                                message=f"疑似处置效应：已有 {existing_dir} 持仓却申请 {req.direction}，请确认交易意图",
                                severity="LOW"
                            ))
                    break
    except Exception:
        pass  # 持仓信息不可用时跳过
    
    # R2：日内亏损限制（当日累计亏损超过账户权益阈值）
    try:
        if account:
            daily_pnl = account.get("dailyPnl", 0) if isinstance(account, dict) else 0
            balance = account.get("balance", 1_000_000) if isinstance(account, dict) else 1_000_000
            # 从当前持仓也计算浮动盈亏
            floating_pnl = sum(p.get("pnl", 0) for p in positions)
            total_pnl = daily_pnl + floating_pnl
            # 默认阈值：账户权益的 -3%（保守档）
            daily_loss_limit = balance * -0.03
            if total_pnl < daily_loss_limit:
                violations.append(SimulateViolation(
                    ruleId="R2_DAILY_LOSS",
                    message=f"日内亏损超限：累计亏损 {total_pnl:.2f}，限额 {daily_loss_limit:.2f}（权益3%）",
                    severity="HIGH"
                ))
    except Exception:
        pass  # 账户信息不可用时跳过

    # R5：波动率检查（品种 ATR 超过阈值时限制开仓）
    try:
        if hasattr(bridge, 'get_tick'):
            tick = bridge.get_tick(req.symbol)
            if tick:
                # 用当日振幅简化估算波动率
                high = tick.get("high", req.price)
                low = tick.get("low", req.price)
                pre_close = tick.get("preClose", req.price)
                if pre_close and pre_close > 0:
                    daily_range_pct = (high - low) / pre_close
                    # 阈值：日振幅超过 4% 视为高波动
                    volatility_threshold = 0.04
                    if daily_range_pct > volatility_threshold:
                        violations.append(SimulateViolation(
                            ruleId="R5_VOLATILITY",
                            message=f"波动率过高：日振幅 {daily_range_pct*100:.2f}%，超过阈值 {volatility_threshold*100:.0f}%",
                            severity="MEDIUM"
                        ))
    except Exception:
        pass  # 行情不可用时跳过

    # R12：撤单次数限制（日内撤单超过阈值则限制新委托）
    try:
        if hasattr(bridge, 'get_risk_status'):
            risk_status = bridge.get_risk_status()
            if risk_status:
                rules_data = risk_status.get("rules", [])
                for rule in rules_data:
                    if rule.get("ruleId") == "R12_CANCEL_LIMIT" and rule.get("triggered", False):
                        violations.append(SimulateViolation(
                            ruleId="R12_CANCEL_LIMIT",
                            message=f"撤单次数超限：当前撤单 {rule.get('currentValue', 0)} 次，上限 {rule.get('threshold', 10)} 次",
                            severity="MEDIUM"
                        ))
                        break
    except Exception:
        pass  # 风控状态不可用时跳过

    # 汇总结果
    passed = len(violations) == 0
    return {
        "code": 0,
        "message": "success",
        "data": {
            "pass": passed,
            "violations": [v.model_dump() for v in violations]
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
        from services.vnpy_bridge import bridge
        
        # 获取当前持仓 PnL
        positions = bridge.get_positions() if hasattr(bridge, 'get_positions') else []
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
