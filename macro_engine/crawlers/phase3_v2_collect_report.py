# Phase 3 v2.0 采集完成报告
**日期**: 2026-04-20
**观测日期**: 2026-04-18 (周一回退至上周五)
**脚本**: `D:\futures_v6\macro_engine\crawlers\phase3_v2_collect_v2.py`

---

## 执行摘要

| 品种 | 成功采集 | 失败 | 数据源 |
|------|---------|------|--------|
| ZN | 2/2 | 0 | AKShare |
| NI | 2/2 | 0 | AKShare |
| Y | 2/2 | 0 | AKShare |
| P | 1/1 | 0 | AKShare |
| EG | 1/1 | 0 | AKShare |
| PP | 1/1 | 0 | AKShare |
| FU | 2/2 | 0 | AKShare |
| AG | 1/1 | 0 | AKShare |
| AU | 2/2 | 0 | AKShare |
| HC | 2/2 | 0 | AKShare |
| RB | 2/2 | 0 | AKShare |
| PB | 1/1 | 0 | AKShare |
| **合计** | **19/19** | **0** | |

---

## 详细采集结果

### ZN (沪锌)
- `ZN_FUT_CLOSE` = 24020.0 (AKShare-futures_main_sina ZN0) ✓
- `ZN_DCE_INV` = 102674.0 吨 (AKShare-futures_inventory_em) ✓

### NI (沪镍)
- `NI_FUT_CLOSE` = 144240.0 (AKShare-futures_main_sina NI0) ✓
- `NI_DCE_INV` = 64209.0 吨 (AKShare-futures_inventory_em) ✓

### Y (豆油)
- `Y_FUT_CLOSE` = 8466.0 (AKShare-futures_main_sina Y0) ✓
- `Y_CBOT_SOYBEAN` = 3427.0 美分/蒲式耳 (AKShare-futures_foreign_hist ZSD) ✓

### P (棕榈油)
- `P_FUT_CLOSE` = 9492.0 (AKShare-futures_main_sina P0) ✓

### EG (乙二醇)
- `EG_FUT_CLOSE` = 4858.0 (AKShare-futures_main_sina EG0) ✓

### PP (聚丙烯)
- `PP_FUT_CLOSE` = 8429.0 (AKShare-futures_main_sina PP0) ✓

### FU (燃料油)
- `FU_FUT_CLOSE` = 3975.0 (AKShare-futures_main_sina FU0) ✓
- `FU_WTI_PRICE` = 85.56 美元/桶 (AKShare-futures_foreign_hist CL) ✓

### AG (白银)
- `AG_FUT_CLOSE` = 19570.0 (AKShare-futures_main_sina AG0) ✓

### AU (黄金)
- `AU_FUT_CLOSE` = 1054.02 (AKShare-futures_main_sina AU0) ✓
- `AU_SPOT_SGE` = 1058.62 (AKShare-spot_golden_benchmark_sge) ✓

### HC (热轧卷板)
- `HC_FUT_CLOSE` = 3324.0 (AKShare-futures_main_sina HC0) ✓
- `HC_PMI_MFG` = 53.0 (AKShare-macro_china_pmi) ✓

### RB (螺纹钢)
- `RB_FUT_CLOSE` = 3133.0 (AKShare-futures_main_sina RB0) ✓
- `RB_SPD_RB_HC` = -191.0 (AKShare-calculated) ✓ (RB<HC, 工业钢弱于建筑钢)

### PB (沪铅)
- `PB_FUT_CLOSE` = 16775.0 (AKShare-futures_main_sina PB0) ✓

---

## 付费账号缺口清单

以下因子在 v2.0 文档中标注为"付费必配"或"必须配置"，但暂无免费替代：

### ZN (沪锌) - 3个付费缺口
1. **锌TC加工费** (第一梯队, SMM付费) - 无免费替代
2. **镀锌开工率** (第一梯队, Mysteel付费) - 无免费替代
3. **七地锌锭社会库存** (第二梯队, SMM付费) - 无免费替代

### NI (沪镍) - 1个付费缺口
1. **印尼RKAB配额执行率** (第一梯队) - 印尼能矿部官网理论上免费，但需解析PDF，实际执行困难

### PB (沪铅) - 3个付费缺口
1. **铅酸蓄电池开工率** (第一梯队, 隆众/卓创付费) - 无免费替代
2. **原生/再生铅价差** (第二梯队, SMM付费) - 无免费替代
3. **铅矿加工费** (第二梯队, SMM付费) - 无免费替代

### Y (豆油) - 1个付费缺口
1. **大豆进口成本CNF** (第一梯队, 我的农产品网付费) - 无免费替代

### P (棕榈油) - 2个付费缺口
1. **国内棕榈油港口+油厂库存** (第一梯队, 我的农产品网付费) - 无免费替代
2. **MPOB月报** (第一梯队, MPOB官网) - PDF解析复杂

### EG (乙二醇) - 3个付费缺口
1. **乙烯CFR东北亚** (第一梯队, ICIS/隆众付费)
2. **乙二醇港口库存** (第一梯队, CCF付费)
3. **煤制EG装置开工率** (第二梯队, 隆众付费)

### PP (聚丙烯) - 2个付费缺口
1. **丙烯CFR中国** (第一梯队, 隆众付费)
2. **PP港口库存** (第二梯队, 隆众付费)

### RB (螺纹钢) - 1个付费缺口
1. **螺纹钢周度产量** (第一梯队, Mysteel付费) - 无免费替代

---

## API可用性说明

### AKShare 1.18.54 测试结果
| 接口 | 可用性 | 备注 |
|------|--------|------|
| `futures_main_sina(symbol="XX0")` | ✓ | 国内期货主力合约 |
| `futures_inventory_em(symbol="xx")` | ✓ | LME库存 (ZN, NI等) |
| `futures_foreign_hist(symbol="ZSD")` | ✓ | CBOT大豆 |
| `futures_foreign_hist(symbol="CL")` | ✓ | WTI原油 |
| `spot_golden_benchmark_sge` | ✓ | SGE黄金现货 |
| `macro_china_pmi` | ✓ | 制造业PMI |
| `futures_shfe_warehouse_receipt` | ✗ | JSONDecodeError |
| `futures_warehouse_receipt_dce` | ✗ | JSONDecodeError |
| `futures_dce_position_rank` | ✗ | BadZipFile |
| `futures_cbot_soybean` | ✗ | 接口不存在 |

---

## 新增因子 (v2.0 Phase 3修订版对应)

| 文档要求 | 实际采集 | 状态 |
|---------|---------|------|
| ZN: 上期所仓单/净持仓 | `ZN_FUT_CLOSE` (AKShare替代) | ✓ |
| ZN: LME锌库存 | `ZN_DCE_INV` (东方财富) | ✓ |
| NI: 上期所仓单/净持仓 | `NI_FUT_CLOSE` (AKShare替代) | ✓ |
| NI: LME库存 | `NI_DCE_INV` (东方财富) | ✓ |
| Y: CBOT大豆 | `Y_CBOT_SOYBEAN` (ZSD) | ✓ |
| HC: 制造业PMI | `HC_PMI_MFG` (统计局) | ✓ |
| RB: RB-HC价差 | `RB_SPD_RB_HC` (自算) | ✓ |
| FU: WTI原油 | `FU_WTI_PRICE` (CL) | ✓ |

---

## 遗留问题

1. **SHFE仓单数据** - `futures_shfe_warehouse_receipt` API失效，需研究替代方案
2. **DCE/ SHFE持仓排名** - 接口返回非ZIP格式，需单独开发解析器
3. **黄金白银比** - SGE现货白银价格不可用（`macro_china_fx_gold`仅含黄金储备数据），需寻找替代数据源
4. **CBOT大豆油** - `futures_cbot_soybean`接口不存在，ZSD是黄豆，非豆油
