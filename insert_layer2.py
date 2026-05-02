#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Layer 2 规则插入脚本
"""

# 读取当前文件
with open('core/risk/risk_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Layer 2 代码
layer2_code = r'''

# ==================== Layer 2: 账户级风险 ====================

class R2_DailyLossLimitRule(RiskRule):
    """
    R2: 单日最大亏损限制
    当日累计亏损 >= 账户权益的2.5% 或 >= 5000元（取较大值）→ 禁止开仓
    仅检查开仓订单，平仓不受限制
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.limit_ratio = config.get('limit', 0.025)  # 2.5%
        self.absolute_min = config.get('absolute_min', 5000)  # 5000元
        
    def check(self, order, context):
        # 仅对开仓订单进行检查
        if order.offset != "OPEN":
            return self._create_result(
                RiskAction.PASS,
                "平仓订单，跳过单日亏损检查",
                symbol=order.symbol
            )
        
        # 获取账户权益和当日盈亏
        if not context.account:
            return self._create_result(
                RiskAction.PASS,
                "无账户信息，跳过单日亏损检查",
                symbol=order.symbol
            )
        
        equity = context.account.get('equity', 0)
        daily_pnl = context.account.get('daily_pnl', 0)  # 当日累计盈亏（负数为亏损）
        
        if equity <= 0:
            return self._create_result(
                RiskAction.PASS,
                "账户权益无效，跳过检查",
                equity=equity
            )
        
        # 计算亏损阈值（取比例和绝对值的较大值）
        threshold_ratio = equity * self.limit_ratio
        threshold = max(threshold_ratio, self.absolute_min)
        
        # 检查当日亏损是否超过阈值（daily_pnl为负表示亏损）
        if daily_pnl < 0 and abs(daily_pnl) >= threshold:
            return self._create_result(
                RiskAction.BLOCK,
                f"单日亏损超限：当日亏损{abs(daily_pnl):.0f}元 >= 阈值{threshold:.0f}元（权益{equity:.0f}的{self.limit_ratio*100:.1f}%或{self.absolute_min}元）",
                daily_pnl=daily_pnl,
                threshold=threshold,
                equity=equity,
                limit_ratio=self.limit_ratio,
                absolute_min=self.absolute_min
            )
        
        return self._create_result(
            RiskAction.PASS,
            f"单日亏损检查通过：当日盈亏{daily_pnl:.0f}元，阈值{threshold:.0f}元",
            daily_pnl=daily_pnl,
            threshold=threshold
        )


class R7_ConsecutiveLossRule(RiskRule):
    """
    R7: 连续亏损次数限制
    连续亏损 >= 5次 → 暂停交易（禁止开仓）
    连续盈利 >= 3次 → 恢复交易
    仅检查开仓订单
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.base_limit = config.get('base', 5)  # 基础限制5次
        self.recover_after = config.get('recover_after', 3)  # 连续3次盈利恢复
        self.consecutive_losses = 0  # 当前连续亏损次数
        self.consecutive_wins = 0    # 当前连续盈利次数
        self.is_paused = False       # 是否暂停交易
        
    def update_trade_result(self, pnl):
        """更新交易结果（由外部调用）"""
        if pnl > 0:
            # 盈利
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            
            # 连续盈利达到恢复阈值，解除暂停
            if self.is_paused and self.consecutive_wins >= self.recover_after:
                self.is_paused = False
                self.consecutive_wins = 0
                
        elif pnl < 0:
            # 亏损
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            
            # 连续亏损达到限制，暂停交易
            if self.consecutive_losses >= self.base_limit:
                self.is_paused = True
        
        # pnl == 0 时不变
        
    def check(self, order, context):
        # 仅对开仓订单进行检查
        if order.offset != "OPEN":
            return self._create_result(
                RiskAction.PASS,
                "平仓订单，跳过连续亏损检查",
                symbol=order.symbol
            )
        
        # 检查是否处于暂停状态
        if self.is_paused:
            return self._create_result(
                RiskAction.BLOCK,
                f"交易暂停：连续亏损{self.consecutive_losses}次 >= 限制{self.base_limit}次，需连续盈利{self.recover_after}次恢复",
                consecutive_losses=self.consecutive_losses,
                limit=self.base_limit,
                recover_after=self.recover_after,
                consecutive_wins=self.consecutive_wins
            )
        
        # 检查是否即将达到限制（预警）
        if self.consecutive_losses >= self.base_limit - 1:
            return self._create_result(
                RiskAction.WARN,
                f"连续亏损预警：当前{self.consecutive_losses}次，再亏损1次将暂停交易",
                consecutive_losses=self.consecutive_losses,
                limit=self.base_limit
            )
        
        return self._create_result(
            RiskAction.PASS,
            f"连续亏损检查通过：当前{self.consecutive_losses}次，限制{self.base_limit}次",
            consecutive_losses=self.consecutive_losses,
            limit=self.base_limit
        )


class R11_DispositionEffectRule(RiskRule):
    """
    R11: 处置效应监控
    亏损持仓占比 >= 50% 且试图反向开仓 → WARN（提示处置效应风险）
    基于行为金融学：投资者倾向于过早卖出盈利持仓、过久持有亏损持仓
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.drawdown_threshold = config.get('drawdown_threshold', 0.50)  # 50%
        
    def check(self, order, context):
        # 获取持仓盈亏信息
        if not context.positions:
            return self._create_result(
                RiskAction.PASS,
                "无持仓，跳过处置效应检查",
                symbol=order.symbol
            )
        
        # 计算亏损持仓占比
        total_positions = len(context.positions)
        losing_positions = 0
        
        for symbol, pos in context.positions.items():
            if pos == 0:
                continue
                
            # 获取持仓成本和当前价格
            cost_price = context.market_data.get(f'{symbol}_cost_price', 0)
            current_price = context.market_data.get(f'{symbol}_price', 0)
            
            if cost_price > 0 and current_price > 0:
                # 多头持仓：当前价 < 成本价 → 亏损
                if pos > 0 and current_price < cost_price:
                    losing_positions += 1
                # 空头持仓：当前价 > 成本价 → 亏损
                elif pos < 0 and current_price > cost_price:
                    losing_positions += 1
        
        # 计算亏损占比
        loss_ratio = losing_positions / total_positions if total_positions > 0 else 0
        
        # 检查是否触发处置效应预警
        if loss_ratio >= self.drawdown_threshold:
            # 检查是否是反向开仓（可能加剧处置效应）
            is_reverse = False
            current_symbol_pos = context.positions.get(order.symbol, 0)
            
            if current_symbol_pos != 0:
                # 当前有持仓，检查是否反向
                if (current_symbol_pos > 0 and order.direction == "SHORT" and order.offset == "OPEN") or \
                   (current_symbol_pos < 0 and order.direction == "LONG" and order.offset == "OPEN"):
                    is_reverse = True
            
            if is_reverse:
                return self._create_result(
                    RiskAction.WARN,
                    f"处置效应预警：亏损持仓占比{loss_ratio*100:.0f}% >= {self.drawdown_threshold*100:.0f}%，反向开仓可能加剧亏损",
                    loss_ratio=loss_ratio,
                    threshold=self.drawdown_threshold,
                    losing_positions=losing_positions,
                    total_positions=total_positions,
                    is_reverse=True
                )
            else:
                return self._create_result(
                    RiskAction.WARN,
                    f"处置效应提示：亏损持仓占比{loss_ratio*100:.0f}% >= {self.drawdown_threshold*100:.0f}%，建议审视持仓",
                    loss_ratio=loss_ratio,
                    threshold=self.drawdown_threshold,
                    losing_positions=losing_positions,
                    total_positions=total_positions,
                    is_reverse=False
                )
        
        return self._create_result(
            RiskAction.PASS,
            f"处置效应检查通过：亏损持仓占比{loss_ratio*100:.0f}% < {self.drawdown_threshold*100:.0f}%",
            loss_ratio=loss_ratio,
            threshold=self.drawdown_threshold
        )
'''

# 在 Layer 3 之前插入 Layer 2
marker = '# ==================== Layer 3: 交易执行风险 ===================='
if marker in content:
    content = content.replace(marker, layer2_code + '\n' + marker)
    print('Layer 2 code inserted before Layer 3')
else:
    print('ERROR: Could not find Layer 3 marker')
    exit(1)

# 更新规则类映射
old_mapping = """        rule_classes = {
            'R10': R10_MacroFuseRule,
            'R5': R5_VolatilityFilterRule,
            'R6': R6_LiquidityCheckRule,
            'R8': R8_TradingTimeRule,
            'R3': R3_PriceLimitRule,
            'R1': R1_PositionLimitRule,
            'R4': R4_TotalMarginRule,
            'R9': R9_CapitalAdequacyRule,
            # Layer 2 rules will be added in Phase 2
        }"""

new_mapping = """        rule_classes = {
            'R10': R10_MacroFuseRule,
            'R5': R5_VolatilityFilterRule,
            'R6': R6_LiquidityCheckRule,
            'R8': R8_TradingTimeRule,
            'R3': R3_PriceLimitRule,
            'R2': R2_DailyLossLimitRule,
            'R7': R7_ConsecutiveLossRule,
            'R11': R11_DispositionEffectRule,
            'R1': R1_PositionLimitRule,
            'R4': R4_TotalMarginRule,
            'R9': R9_CapitalAdequacyRule,
        }"""

if old_mapping in content:
    content = content.replace(old_mapping, new_mapping)
    print('Rule class mapping updated')
else:
    print('ERROR: Could not find rule class mapping')
    exit(1)

# 写回文件
with open('core/risk/risk_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Layer 2 rules added successfully!')
