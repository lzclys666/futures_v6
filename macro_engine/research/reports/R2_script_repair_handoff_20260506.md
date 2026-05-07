# R2 脚本修复交付文档
**日期**：2026-05-06  
**交付人**：因子分析师YIYI  
**接收人**：程序员mimo (agent-d4f65f0e)

## 背景
健康检查发现 12 个品种 30 天有效因子 < 10，根因分析确认：
- R1 已修复（db_utils.py 置信度封锁）
- R2 目标：修复 SHFE/DCE 免费 API 脚本，让已有的爬虫脚本能正常产出数据

## 已验证可用的 AKShare API

| AKShare 函数 | 适用品种 | 用途 | 验证结果 |
|-------------|---------|------|---------|
| `ak.get_shfe_rank_table(date="20260430")` | PB/HC 等 SHFE 品种 | 持仓排名（前20多空净持仓） | ✅ PB 验证通过 |
| `ak.futures_shfe_warehouse_receipt()` | PB/HC | SHFE 仓单 | ⚠️ 之前测试 JSON 解析失败，需重试 |
| `ak.get_shfe_daily(date)` | PB/HC | SHFE 日度数据 | 未测试 |

## 需要修复的脚本

### PB（沪铅）— 12 个脚本，4 个待修复
| 脚本 | 问题 | 建议修复方向 |
|------|------|------------|
| `PB_沪铅期货净持仓.py` | SHFE 接口需换为 `get_shfe_rank_table` | 已半修复，fetch 逻辑需完整重写 |
| `PB_基差.py` | SHFE 接口待验证 | 尝试 `futures_to_spot_shfe` 或回退到新浪 |
| `PB_月差.py` | SHFE 接口待验证 | 尝试 `futures_spread` |
| `PB_仓单.py` | SHFE 接口待验证 | 尝试 `futures_shfe_warehouse_receipt` |

### HC（热轧卷板）— 13 个脚本
- HC 脚本都有 FACTOR_CODE，运行状况不明
- 对照 PB 模式修复 SHFE API 调用

### PP（聚丙烯）/ Y（豆油）— 11/10 个脚本
- **关键问题**：多个脚本缺少 FACTOR_CODE 定义
- 需要对照交付文档补全 FCODE + 修复 DCE API 调用

## 修复优先级
1. PB 净持仓 — 最接近完成，逻辑已验证
2. PB 仓单/基差/月差 — 3 个 SHFE 接口脚本
3. PP + Y — FACTOR_CODE 缺失 + DCE 接口
4. HC — 基线检查 + SHFE 接口

## 技术提示
- `get_shfe_rank_table` 只在交易日返回数据，需加 10 天以上回退（覆盖长假）
- `get_shfe_rank_table` 返回 dict，key 为合约代码（如 pb2607）
- 中文文件名在 PowerShell 中有 GBK 编码问题，在 Python 脚本中 `open(path, encoding='utf-8')` 可正常读写
