# P0 Fix Summary - SignalChart Field Normalization

**Task**: Fix P0 issues in `macro_scoring_engine.py` where Mock and CSV paths returned inconsistent field names, breaking the frontend `FactorDetail` interface.

**Root Cause**: 
- `_build_factor_details_from_csv()` returned snake_case (`factor_code`, `factor_value`, `factor_weight`, `factor_direction`, `raw_value`, `factor_ic`)
- `_build_factor_details_from_mock()` returned camelCase but used `contributionPolarity` instead of `direction`
- Internal composite_score calculations in `get_signal` and `get_all_signals` accessed snake_case keys (`factor_value`/`factor_weight`) that no longer existed after fixing the builders

**Fixes Applied** (all in `D:\futures_v6\api\macro_scoring_engine.py`):

| # | Location | Change |
|---|----------|--------|
| 1 | `_build_factor_details_from_csv()` | All 8 fields → camelCase (`factorCode`, `factorName`, `direction`, `rawValue`, `normalizedScore`, `weight`, `contribution`, `factorIc`) |
| 2 | `_build_factor_details_from_mock()` | `contributionPolarity` → `direction` (matches frontend `FactorDetail.direction`) |
| 3 | `get_signal()` mock fallback (L430) | `f["factor_value"]*f["factor_weight"]` → `f["normalizedScore"]*f["weight"]` |
| 4 | `get_signal()` yesterday fallback (L423) | same field name fix |
| 5 | `get_all_signals()` fallback paths (×2) | same field name fix |

**Result**: Both Mock and CSV paths now return identical camelCase field names exactly matching the frontend `FactorDetail` TypeScript interface.

**File**: `D:\futures_v6\api\macro_scoring_engine.py`
