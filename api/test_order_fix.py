"""
测试订单接口字段修复
验证：
1. offset 默认值 "OPEN" 生效
2. symbol 自动补全为 vt_symbol
"""
import sys
sys.path.insert(0, ".")

from routes.trading import OrderRequest

def test_offset_default():
    """测试 offset 默认值"""
    # 前端只发 symbol + direction + price + volume，不发 offset
    req = OrderRequest(
        symbol="CU",
        direction="LONG",
        price=75000.0,
        volume=1
    )
    assert req.offset == "OPEN", f"offset 默认值应为 OPEN，实际为 {req.offset}"
    print("[PASS] offset 默认值测试通过: offset=OPEN")

def test_symbol_completion():
    """测试 symbol 自动补全"""
    test_cases = [
        ("CU", "SHFE.CU2505"),
        ("AU", "SHFE.AU2506"),
        ("AG", "SHFE.AG2506"),
        ("ZN", "SHFE.ZN2505"),
        ("RU", "SHFE.RU2505"),
        ("cu", "SHFE.CU2505"),  # 小写自动转大写
        ("UNKNOWN", "SHFE.UNKNOWN2505"),  # 未知品种
    ]
    
    for symbol, expected_vt in test_cases:
        req = OrderRequest(
            symbol=symbol,
            direction="LONG",
            price=50000.0,
            volume=1
        )
        actual_vt = req.get_symbol()
        assert actual_vt == expected_vt, f"symbol={symbol} 应补全为 {expected_vt}，实际为 {actual_vt}"
        print(f"[PASS] symbol 补全测试通过: {symbol} -> {actual_vt}")

def test_explicit_vt_symbol():
    """测试显式 vt_symbol 优先"""
    req = OrderRequest(
        symbol="CU",
        vt_symbol="SHFE.CU2506",  # 显式指定
        direction="SHORT",
        offset="CLOSE",
        price=75000.0,
        volume=2
    )
    assert req.get_symbol() == "SHFE.CU2506", "显式 vt_symbol 应优先"
    assert req.offset == "CLOSE", "显式 offset 应覆盖默认值"
    print("[PASS] 显式 vt_symbol 和 offset 测试通过")

def test_close_offset():
    """测试平仓 offset"""
    req = OrderRequest(
        symbol="AU",
        direction="SHORT",
        offset="CLOSE",  # 显式平仓
        price=500.0,
        volume=1
    )
    assert req.offset == "CLOSE", "平仓 offset 应为 CLOSE"
    print("[PASS] 平仓 offset 测试通过")

if __name__ == "__main__":
    print("=" * 60)
    print("订单接口字段修复测试")
    print("=" * 60)
    
    test_offset_default()
    test_symbol_completion()
    test_explicit_vt_symbol()
    test_close_offset()
    
    print("=" * 60)
    print("[SUCCESS] 所有测试通过! 修复成功")
    print("=" * 60)
