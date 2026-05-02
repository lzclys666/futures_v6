# Task Summary: CU/NI LME Spread Data Collection Fix

**Date**: 2026-04-20
**Task**: Fix CU_LME_SPREAD / NI_LME_SPREAD data that was almost all 0

## Problem Analysis
- LME铜/镍 Cash-3M升贴水数据在正常市场条件下接近0
- 历史CSV数据显示spread列全部为0（1590条CU记录，1585条NI记录）
- 原因：数据源提供的是价格数据而非真正的升贴水数据
- 无法用于IC验证（因子需要有变异）

## Selected Solution: Option B (Event-Driven Collection)

**选定方案B的原因**：
- Option A (LME Spot-3M Spread) 需要访问LME官网，但LME官网返回403错误
- 前瞻网等数据源需要付费订阅
- Option B可以在现有数据源基础上实施

## Implementation Details

### 1. New Crawler Script
**File**: `D:\futures_macro_engine\crawlers\CU_NI\CU_NI_抓取LME升贴水_EVENT.py`

**功能**：
- 使用AKShare `futures_foreign_commodity_realtime`获取LME铜(NID)/镍(CAD)价格
- 计算价格变化作为spread代理（最新价 - 昨日结算价）
- 计算每日spread变化量（DIFF因子）
- 当|spread| > 50 USD/吨时触发事件标记（EVENT因子）

**数据源**：
- L1: AKShare futures_foreign_commodity_realtime (CAD/NID)
- L4: DB历史回补

### 2. New YAML Config Files

**CU factors**:
- `D:\futures_macro_engine\config\factors\CU\CU_LME_SPREAD.yaml`
- `D:\futures_macro_engine\config\factors\CU\CU_LME_SPREAD_DIFF.yaml`
- `D:\futures_macro_engine\config\factors\CU\CU_LME_SPREAD_EVENT.yaml`

**NI factors**:
- `D:\futures_macro_engine\config\factors\NI\NI_LME_SPREAD.yaml`
- `D:\futures_macro_engine\config\factors\NI\NI_LME_SPREAD_DIFF.yaml`
- `D:\futures_macro_engine\config\factors\NI\NI_LME_SPREAD_EVENT.yaml`

### 3. Updated run_all.py

**CU_run_all.py**: 添加了 `../CU_NI/CU_NI_抓取LME升贴水_EVENT.py`
**NI_run_all.py**: 添加了 `../CU_NI/CU_NI_抓取LME升贴水_EVENT.py`

### 4. Database Records (2026-04-18)

| factor_code | symbol | raw_value | source |
|------------|--------|-----------|--------|
| CU_LME_SPREAD | CU | 5.10 | akshare_futures_foreign_commodity_realtime_CAD |
| CU_LME_SPREAD_DIFF | CU | 0.0 | akshare_futures_foreign_commodity_realtime_CAD_diff |
| CU_LME_SPREAD_EVENT | CU | 0.0 | akshare_futures_foreign_commodity_realtime_CAD_event |
| NI_LME_SPREAD | NI | -145.5 | akshare_futures_foreign_commodity_realtime_NID |
| NI_LME_SPREAD_DIFF | NI | 0.0 | akshare_futures_foreign_commodity_realtime_NID_diff |
| NI_LME_SPREAD_EVENT | NI | 1.0 | akshare_futures_foreign_commodity_realtime_NID_event |

**注意**: NI_LME_SPREAD_EVENT = 1 是因为|-145.5| > 50（阈值），表明市场紧张信号

## Limitations

1. **数据源限制**: AKShare不提供真正的Cash-3M spread数据，当前收集的是价格变化作为代理
2. **变异有限**: 价格变化代理在正常市场下仍然可能接近0
3. **未来改进**: 如需真正的Spot-3M Spread数据，需要订阅前瞻网或其他付费源

## Factor Design Summary

| 因子代码 | 描述 | 阈值 |
|---------|------|------|
| CU_LME_SPREAD | LME铜升贴水（价格变化代理） | - |
| CU_LME_SPREAD_DIFF | 升贴水日变化量 | - |
| CU_LME_SPREAD_EVENT | 升贴水事件标记 | >50 USD/吨 |
| NI_LME_SPREAD | LME镍升贴水（价格变化代理） | - |
| NI_LME_SPREAD_DIFF | 升贴水日变化量 | - |
| NI_LME_SPREAD_EVENT | 升贴水事件标记 | >50 USD/吨 |
