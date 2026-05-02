import sys
sys.path.insert(0, r'D:\futures_v6\api')
from macro_api_server import app
from fastapi.testclient import TestClient

client = TestClient(app)

# 1. 健康检查
print('=== 1. Health Check ===')
r = client.get('/health')
print(f'  Status: {r.status_code}')
print(f'  Body: {r.json()}')
print()

# 2. 宏观信号
print('=== 2. Macro Signal (RU) ===')
r = client.get('/api/macro/signal/RU')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    print(f'  Has data: {"data" in data}')
    if data.get('data'):
        print(f'  Symbol: {data["data"].get("symbol")}')
        print(f'  Score: {data["data"].get("score")}')
else:
    print(f'  Error: {r.text[:200]}')
print()

# 3. 交易接口 - 风控规则
print('=== 3. Risk Rules ===')
r = client.get('/api/trading/risk-rules')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    d = data.get('data', {})
    if isinstance(d, dict):
        rules = d.get('rules', [])
    else:
        rules = d if isinstance(d, list) else []
    print(f'  Rules count: {len(rules)}')
    if rules:
        print(f'  First rule: {rules[0]["id"]} - {rules[0]["name"]}')
print()

# 4. VNpy 状态
print('=== 4. VNpy Status ===')
r = client.get('/api/vnpy/status')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    print(f'  Data: {data.get("data")}')
print()

# 5. 持仓查询（无 VNpy 连接时）
print('=== 5. Positions ===')
r = client.get('/api/trading/positions')
print(f'  Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'  Code: {data.get("code")}')
    print(f'  Data: {data.get("data")}')
