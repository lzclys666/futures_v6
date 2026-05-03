import sys
sys.path.insert(0, r'D:\futures_v6')

from services.vnpy_bridge import get_vnpy_bridge

print("=== VNpy Engine Test ===")
print()

# 1. 启动引擎
print("1. Starting VNpy engine...")
if get_vnpy_bridge().start():
    print("   [OK] VNpy started successfully")
else:
    print("   [FAIL] Failed to start VNpy")
    sys.exit(1)

# 2. 查看状态
print()
print("2. Engine status:")
status = get_vnpy_bridge().get_status()
for k, v in status.items():
    print(f"   {k}: {v}")

# 3. 测试下单（Paper Account）
print()
print("3. Testing order placement...")
vt_orderid = get_vnpy_bridge().send_order(
    vt_symbol="RU2505.SHFE",
    direction="LONG",
    offset="OPEN",
    price=15000.0,
    volume=1
)
if vt_orderid:
    print(f"   [OK] Order sent: {vt_orderid}")
else:
    print("   [WARN] Order failed (expected if no market data)")

# 4. 查询持仓
print()
print("4. Positions:")
positions = get_vnpy_bridge().get_positions()
print(f"   Count: {len(positions)}")
for pos in positions:
    print(f"   {pos}")

# 5. 查询订单
print()
print("5. Orders:")
orders = get_vnpy_bridge().get_orders()
print(f"   Count: {len(orders)}")
for order in orders:
    print(f"   {order}")

# 6. 查询账户
print()
print("6. Account:")
account = get_vnpy_bridge().get_account()
print(f"   {account}")

# 7. 停止引擎
print()
print("7. Stopping VNpy engine...")
if get_vnpy_bridge().stop():
    print("   [OK] VNpy stopped")
else:
    print("   [FAIL] Failed to stop")

print()
print("=== Test Complete ===")
