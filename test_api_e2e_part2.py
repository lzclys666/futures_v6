import sys
sys.path.insert(0, r'D:\futures_v6\api')
from macro_api_server import app
from fastapi.testclient import TestClient

client = TestClient(app)

# 6. 测试下单（带 vt_symbol 字段）
print('=== 6. Place Order (with vt_symbol) ===')
order_req = {
    "vt_symbol": "RU2505.SHFE",
    "direction": "LONG",
    "offset": "OPEN",
    "volume": 1,
    "price": 15000.0
}
r = client.post('/api/trading/order', json=order_req)
print(f'  Status: {r.status_code}')
print(f'  Body: {r.json()}')
print()

# 7. 测试撤单（不存在的订单）
print('=== 7. Cancel Order (Non-existent) ===')
r = client.delete('/api/trading/order/TEST.12345')
print(f'  Status: {r.status_code}')
print(f'  Body: {r.json()}')
print()

# 8. 账户查询
print('=== 8. Account ===')
r = client.get('/api/trading/account')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    print(f'  Data: {data.get("data")}')
print()

# 9. 订单查询
print('=== 9. Orders ===')
r = client.get('/api/trading/orders')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    print(f'  Data: {data.get("data")}')
print()

# 10. 成交查询
print('=== 10. Trades ===')
r = client.get('/api/trading/trades')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    print(f'  Data: {data.get("data")}')
print()

# 11. 风控状态
print('=== 11. Risk Status ===')
r = client.get('/api/risk/status')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    d = data.get('data', {})
    print(f'  Overall: {d.get("overallStatus")}')
    print(f'  Rules count: {len(d.get("rules", []))}')
print()

print('=== E2E Test Complete ===')
