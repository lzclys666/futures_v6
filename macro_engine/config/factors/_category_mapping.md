# YAML Category 双体系映射方案

> 生成日期: 2026-05-02 | 责任人: 项目经理（YIYI超时后PM接管）
> 状态: 待确认

## 1. 现状统计

### 因子 YAML (294个)

| 指标 | 数值 |
|------|------|
| 只有 logic_category | 103 |
| 只有 category | 185 |
| 两者都有 | 0 |
| 两者都没有 | 6 |

### logic_category 分布 (24种)

| 代码 | 含义 | 数量 | 推荐映射 |
|------|------|------|----------|
| STK | 库存 | 16 | free_data |
| STR | 现货价格 | 13 | free_data |
| QTY | 产量/消费量 | 12 | paid_data |
| SPD | 价差 | 9 | derived |
| POS | 持仓 | 8 | free_data |
| FX | 汇率 | 5 | free_data |
| SEN | 情绪/集中度 | 5 | derived |
| DEM | 需求 | 5 | paid_data |
| CST | 成本 | 5 | free_data |
| INV | 库存(交易所) | 4 | free_data |
| TS | 时间序列 | 4 | free_data |
| PRI | 现货价格 | 3 | free_data |
| FRT | 运费 | 2 | free_data |
| SUP | 供给 | 2 | free_data |
| VAL | 估值 | 1 | derived |
| INF | 通胀 | 1 | free_data |
| RAT | 利率 | 1 | free_data |
| CTR | COT持仓 | 1 | free_data |
| ARB | 套利 | 1 | derived |
| WTH | 天气 | 1 | free_data |
| MGN | 利润 | 1 | derived |
| BASIS | 基差 | 1 | derived |
| CROSS | 跨品种 | 1 | derived |
| PRC | 价格 | 1 | free_data |

### category 分布 (14种，旧体系值)

| 值 | 数量 | 性质 |
|----|------|------|
| inventory | 52 | = logic_category 的 INV/STK |
| free_data | 31 | ✅ 已是新体系 |
| spread | 25 | = logic_category 的 SPD |
| price | 21 | = logic_category 的 STR/PRI |
| position | 19 | = logic_category 的 POS |
| supply | 8 | = logic_category 的 SUP |
| operation | 7 | = logic_category 的 SEN(运营率) |
| cost | 7 | = logic_category 的 CST |
| macro | 6 | = logic_category 的 FX/INF/RAT |
| basis | 3 | = logic_category 的 BASIS |
| fx | 2 | = logic_category 的 FX |
| event | 2 | = logic_category 的 CTR |
| warehouse_receipt | 1 | = logic_category 的 STK(仓单) |
| demand | 1 | = logic_category 的 DEM |

## 2. 新 category 枚举定义

| 枚举值 | 含义 | 判定标准 |
|--------|------|----------|
| free_data | 免费公开数据 | AKShare/交易所/FRED/CFTC等免费接口 |
| paid_data | 付费数据 | Mysteel/SMM/MyAgri/付费数据库 |
| derived | 衍生计算指标 | 从原始数据二次计算(价差/基差/利润/集中度等) |
| model_signal | 模型信号 | 由量化模型生成的信号(当前无此类型) |

## 3. 映射规则

### 规则1: 按 logic_category 默认映射

`
STK → free_data      (交易所库存，免费)
STR → free_data      (现货价格，AKShare免费)
QTY → paid_data      (产量/消费量，多来自Mysteel/MyAgri)
SPD → derived        (价差，需二次计算)
POS → free_data      (持仓排名，交易所免费)
FX  → free_data      (汇率，AKShare免费)
SEN → derived        (集中度/净持仓，需二次计算)
DEM → paid_data      (需求，多来自付费数据库)
CST → free_data      (成本，多为公开价格计算)
INV → free_data      (交易所库存，免费)
TS  → free_data      (时间序列原始数据)
PRI → free_data      (现货价格)
FRT → free_data      (运费BDI等，免费)
SUP → free_data      (供给，多为公开数据)
VAL → derived        (估值，需二次计算)
INF → free_data      (通胀CPI等，FRED免费)
RAT → free_data      (利率，FRED免费)
CTR → free_data      (COT持仓，CFTC免费)
ARB → derived        (套利，需二次计算)
WTH → free_data      (天气ENSO，NOAA免费)
MGN → derived        (利润，需二次计算)
BASIS → derived      (基差，需二次计算)
CROSS → derived      (跨品种比价，需二次计算)
PRC → free_data      (价格，免费)
`

### 规则2: 按数据源覆盖映射

当 dependencies 含以下关键词时覆盖默认映射：

| dependency 关键词 | 覆盖为 |
|-------------------|--------|
| Mysteel / SMM / MyAgri / 付费 | paid_data |
| Calculation / 模型 | derived |
| AKShare / 交易所 / FRED / CFTC / NOAA | free_data |

### 规则3: 特殊处理

- QTY(产量) 大部分来自 Mysteel(付费)，但少量来自统计局(免费) → 默认 paid_data，统计局来源单独标 free_data
- SEN(情绪) 的 OI 数据是免费的 → 但集中度/净持仓是计算值 → 默认 derived

## 4. 迁移方案 (方案B)

### 步骤

1. **备份**: 复制整个 config/factors 目录
2. **写入 category**: 根据映射规则，给每个 YAML 写入 category 字段
3. **保留 logic_category**: 暂不删除，作为历史参考
4. **删除旧 category 非标值**: 把 inventory/price/position/spread/... 等旧值替换为标准枚举
5. **修复 expected_range**: 30个文件的格式错误一并修复
6. **验证**: 运行 validate_yaml_schemas.py 确认 0 错误

### expected_range 修复规则

30个文件的 expected_range 格式为单元素字符串列表如 ['-100000-200000']，
修复为双元素数字列表如 [-100000, 200000]。

解析规则：字符串按第一个数字和最后一个数字提取 min/max：
- '-100000-200000' → min=-100000, max=200000
- '50000-500000' → min=50000, max=500000
- '0-1' → min=0, max=1

## 5. 待确认事项

- [ ] YIYI 确认映射规则是否合理（特别是 QTY→paid_data 的默认分类）
- [ ] YIYI 确认是否需要增加 category 枚举值（如 operation/cost 是否应独立）
- [ ] 确认 logic_category 保留策略（暂保留 vs 立即删除）
- [ ] 确认迁移脚本执行时间（建议 5/3 晚间低峰期）
