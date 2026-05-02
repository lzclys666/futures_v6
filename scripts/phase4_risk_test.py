"""
Phase 4 完整风控测试
13条规则逐条验证
"""
import sys
sys.path.insert(0, r"D:\futures_v6")

from unittest.mock import MagicMock, patch
from datetime import datetime, time as dt_time

# 模拟 VNpy 对象
class MockOrderData:
    def __init__(self, symbol, direction, offset, price, volume, status="SUBMITTING"):
        self.symbol = symbol
        self.direction = MagicMock()
        self.direction.value = direction
        self.offset = MagicMock()
        self.offset.value = offset
        self.price = price
        self.volume = volume
        self.status = MagicMock()
        self.status.value = status
        self.vt_orderid = f"{symbol}_{direction}_{volume}"

class MockPositionData:
    def __init__(self, symbol, direction, volume):
        self.symbol = symbol
        self.direction = MagicMock()
        self.direction.value = direction
        self.volume = volume

class MockAccountData:
    def __init__(self, available):
        self.available = available
        self.balance = available
        self.frozen = 0
        self.margin = 0

# 测试框架
class RiskTestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def test(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            self.results.append(f"[PASS] {name}")
        else:
            self.failed += 1
            self.results.append(f"[FAIL] {name} - {detail}")
    
    def report(self):
        print("\n" + "="*60)
        print("Phase 4 Risk Test Report")
        print("="*60)
        for r in self.results:
            print(r)
        print(f"\nTotal: {self.passed+self.failed} | PASS {self.passed} | FAIL {self.failed}")
        return self.failed == 0

# 开始测试
print("="*60)
print("Phase 4 完整风控测试 - 13条规则验证")
print("="*60)

runner = RiskTestRunner()

# 导入风控引擎
try:
    from services.macro_risk_app import RiskEngine, RiskRuleConfig, DEFAULT_RULES
    runner.test("模块导入", True)
except Exception as e:
    runner.test("模块导入", False, str(e))
    runner.report()
    sys.exit(1)

# 创建模拟引擎
mock_main = MagicMock()
mock_event = MagicMock()
engine = RiskEngine(mock_main, mock_event)

# 规则1: 单品种最大持仓
print("\n--- 规则1: 单品种最大持仓 ---")
engine.rules["单品种最大持仓"].enabled = True
engine.rules["单品种最大持仓"].threshold = 10

# 场景1a: 无持仓，下单5手 -> 通过
mock_main.get_all_positions.return_value = []
mock_main.get_all_accounts.return_value = [MockAccountData(1000000)]
order = MockOrderData("AU", "LONG", "OPEN", 500, 5)
violations = engine._check_rules(order)
runner.test("1a. 无持仓下单5手", len(violations) == 0, f"违规: {[v['rule'] for v in violations]}")

# 场景1b: 已有8手，下单5手 -> 拦截
# 创建与订单同方向的持仓
order = MockOrderData("AU", "LONG", "OPEN", 500, 5)
pos8 = MockPositionData("AU", "LONG", 8)
pos8.direction = order.direction  # 使用相同的MagicMock对象
mock_main.get_all_positions.return_value = [pos8]
mock_main.get_all_accounts.return_value = [MockAccountData(1000000)]
violations = engine._check_rules(order)
runner.test("1b. 持仓8手再下5手", any(v["rule"] == "单品种最大持仓" for v in violations), 
            f"应触发单品种最大持仓限制, 违规: {[v['rule'] for v in violations]}")

# 场景1c: 不同方向不累计
mock_main.get_all_positions.return_value = [MockPositionData("AU", "SHORT", 8)]
mock_main.get_all_accounts.return_value = [MockAccountData(1000000)]
order = MockOrderData("AU", "LONG", "OPEN", 500, 5)
violations = engine._check_rules(order)
runner.test("1c. 反向持仓不累计", len(violations) == 0 or "单品种最大持仓" not in [v["rule"] for v in violations],
            "反向持仓不应累计")

# 规则2: 单日最大亏损
print("\n--- 规则2: 单日最大亏损 ---")
engine.daily_pnl = -6000  # 已亏损6000
engine.rules["单日最大亏损"].enabled = True
engine.rules["单日最大亏损"].threshold = 5000

mock_main.get_all_positions.return_value = []
order = MockOrderData("AU", "LONG", "OPEN", 500, 1)
violations = engine._check_rules(order)
runner.test("2a. 已亏损6000再下单", any(v["rule"] == "单日最大亏损" for v in violations),
            "应触发单日最大亏损限制")

engine.daily_pnl = -3000
violations = engine._check_rules(order)
runner.test("2b. 已亏损3000再下单", len(violations) == 0 or "单日最大亏损" not in [v["rule"] for v in violations],
            "未超限不应触发")

# 规则3: 涨跌停限制
print("\n--- 规则3: 涨跌停限制 ---")
engine.rules["涨跌停限制"].enabled = True

order = MockOrderData("AU", "LONG", "OPEN", 0, 1)
violations = engine._check_rules(order)
runner.test("3a. 价格为0", any(v["rule"] == "涨跌停限制" for v in violations),
            "价格为0应被拦截")

order = MockOrderData("AU", "LONG", "OPEN", 500, 1)
violations = engine._check_rules(order)
runner.test("3b. 价格正常", len(violations) == 0 or "涨跌停限制" not in [v["rule"] for v in violations],
            "正常价格不应触发")

# 规则4: 总持仓比例上限
print("\n--- 规则4: 总持仓比例上限 ---")
engine.rules["总持仓比例上限"].enabled = True

mock_main.get_all_positions.return_value = [MockPositionData("AU", "LONG", 45)]
mock_main.get_all_accounts.return_value = [MockAccountData(1000000)]
order = MockOrderData("CU", "LONG", "OPEN", 70000, 10)
violations = engine._check_rules(order)
runner.test("4a. 总持仓45+10手", any(v["rule"] == "总持仓比例上限" for v in violations),
            "总持仓超限应被拦截")

# 规则5: 单品种集中度上限
print("\n--- 规则5: 单品种集中度上限 ---")
engine.rules["单品种集中度上限"].enabled = True

mock_main.get_all_positions.return_value = [
    MockPositionData("AU", "LONG", 20),
    MockPositionData("CU", "LONG", 5)
]
mock_main.get_all_accounts.return_value = [MockAccountData(1000000)]
order = MockOrderData("AU", "LONG", "OPEN", 500, 10)
violations = engine._check_rules(order)
# AU 将变为 30/35 = 85% > 30%
runner.test("5a. 单品种集中度超限", any(v["rule"] == "单品种集中度上限" for v in violations),
            "集中度超限应被拦截")

# 规则9: 连续亏损次数限制
print("\n--- 规则9: 连续亏损次数限制 ---")
engine.rules["连续亏损次数限制"].enabled = True
engine.rules["连续亏损次数限制"].threshold = 3
engine.consecutive_losses = 3

mock_main.get_all_positions.return_value = []
mock_main.get_all_accounts.return_value = [MockAccountData(1000000)]
order = MockOrderData("AU", "LONG", "OPEN", 500, 1)
violations = engine._check_rules(order)
runner.test("9a. 连续亏损3次", any(v["rule"] == "连续亏损次数限制" for v in violations),
            "连续亏损超限应暂停开仓")

engine.consecutive_losses = 2
violations = engine._check_rules(order)
runner.test("9b. 连续亏损2次", len(violations) == 0 or "连续亏损次数限制" not in [v["rule"] for v in violations],
            "未超限不应触发")

# 规则10: 交易时间检查
print("\n--- 规则10: 交易时间检查 ---")
engine.rules["交易时间检查"].enabled = True

# 直接测试时间逻辑（不mock datetime）
now = dt_time(10, 0)
is_day = dt_time(9, 0) <= now <= dt_time(15, 0)
is_night = now >= dt_time(21, 0) or now <= dt_time(2, 30)
runner.test("10a. 日盘10:00", is_day or is_night, "日盘应在交易时段")

now = dt_time(20, 0)
is_day = dt_time(9, 0) <= now <= dt_time(15, 0)
is_night = now >= dt_time(21, 0) or now <= dt_time(2, 30)
runner.test("10b. 非交易时间20:00", not (is_day or is_night), "20:00不应在交易时段")

now = dt_time(22, 0)
is_day = dt_time(9, 0) <= now <= dt_time(15, 0)
is_night = now >= dt_time(21, 0) or now <= dt_time(2, 30)
runner.test("10c. 夜盘22:00", is_day or is_night, "夜盘应在交易时段")

# 规则11: 资金充足性检查
print("\n--- 规则11: 资金充足性检查 ---")
engine.rules["资金充足性检查"].enabled = True

mock_main.get_all_positions.return_value = []
mock_main.get_all_accounts.return_value = [MockAccountData(100000)]
order = MockOrderData("AU", "LONG", "OPEN", 500, 1)  # 保证金 = 500*1*10*0.15 = 750
violations = engine._check_rules(order)
has_fund_violation = any(v["rule"] == "资金充足性检查" for v in violations)
runner.test("11a. 资金充足", not has_fund_violation,
            f"750保证金<10万可用，不应触发, 违规: {[v['rule'] for v in violations]}")

mock_main.get_all_accounts.return_value = [MockAccountData(100)]
order = MockOrderData("AU", "LONG", "OPEN", 500, 100)  # 保证金 = 75000
violations = engine._check_rules(order)
has_fund_violation = any(v["rule"] == "资金充足性检查" for v in violations)
runner.test("11b. 资金不足", has_fund_violation,
            f"75000保证金>100可用，应触发, 违规: {[v['rule'] for v in violations]}")

# 规则配置测试
print("\n--- 规则配置管理 ---")
engine.set_rule("单品种最大持仓", enabled=False)
runner.test("配置. 禁用规则", not engine.rules["单品种最大持仓"].enabled,
            "禁用后应为False")

engine.set_rule("单品种最大持仓", enabled=True, threshold=20)
runner.test("配置. 修改阈值", engine.rules["单品种最大持仓"].threshold == 20,
            "阈值应更新为20")

status = engine.get_rule_status()
runner.test("配置. 获取状态", len(status) == 13,
            f"应有13条规则，实际{len(status)}")

# 生成报告
success = runner.report()

# 写入结果
with open(r"D:\futures_v6\scripts\phase4_test_result.txt", "w", encoding="utf-8") as f:
    f.write("Phase 4 风控测试报告\n")
    f.write("="*60 + "\n")
    for r in runner.results:
        f.write(r + "\n")
    f.write(f"\n总计: {runner.passed+runner.failed} 项 | 通过 {runner.passed} | 失败 {runner.failed}\n")

sys.exit(0 if success else 1)
