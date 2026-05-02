import requests
import json

# 测试 IC 热力图 API
response = requests.get('http://localhost:8002/api/ic/heatmap?symbols=JM,RU,RB,ZN,NI')
data = response.json()

print('IC Heatmap Response:')
print(f"  Factors: {data['factors']}")
print(f"  Symbols: {data['symbols']}")
print(f"  Lookback: {data['lookbackPeriod']}")
print(f"  Hold Period: {data['holdPeriod']}")
print(f"  Updated: {data['updatedAt']}")
print()
print('IC Matrix:')
header = 'Factor'.ljust(16)
for sym in data['symbols']:
    header += sym.ljust(12)
print(header)
print('-' * 80)
for i, factor in enumerate(data['factors']):
    row = data['icMatrix'][i]
    line = factor.ljust(16)
    for val in row:
        line += f'{val:+.4f}'.ljust(12)
    print(line)
