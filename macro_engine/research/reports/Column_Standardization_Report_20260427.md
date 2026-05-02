# Column Standardization Report — 2026-04-27

## Summary

任务完成：9个CSV文件列名已标准化，所有文件均有 `.bak` 备份。

---

## 修改清单

| 文件 | 原列名 | 新列名 | 状态 |
|------|--------|--------|------|
| `Brent_crude.csv` | `wti_spot_usd_bbl` | `price` | ✅ 完成 |
| `USD_CNY_spot.csv` | `usd_cny` | `price` | ✅ 完成 |
| `CN_10Y_bond_yield.csv` | `cn_10y_yield` | `price` | ✅ 完成 |
| `CN_10Y_bond_yield_v2.csv` | `DATE, DSWP10` | `date, price` | ✅ 完成 |
| `AU_AG_ratio_corrected.csv` | `au_ag_ratio_corrected` | `ratio` | ✅ 完成 |
| `AU_AG_ratio_v2.csv` | `au_ag_ratio_g_per_g` | `ratio` | ✅ 完成 |
| `AG/daily/usd_index.csv` | `value` | `price` | ✅ 完成 |
| `AU/daily/AU_SGE_SHFE_spread.csv` | `close_sge, close_fut, sge_fut_spread` | `sge_price, fut_price, spread` | ✅ 完成 |
| `JM/daily/JM10_jm_zc_ratio.csv` | `日期, JM_close, ZC_close` | `date, jm_close, zc_close` | ✅ 完成 |

---

## 未修改文件（无需修改）

### OHLCV文件（列名已标准）
以下文件列名已符合规范（`date,open,high,low,close,volume,hold`），Pandera验证FAIL由数据质量问题（null值/零值）导致，非列名问题：

| 文件 | 类型 |
|------|------|
| `AG_fut_close.csv` | OHLCV |
| `AL_fut_close.csv` | OHLCV |
| `AO_fut_close.csv` | OHLCV |
| `AU_fut_close.csv` | OHLCV |
| `BR_fut_close.csv` | OHLCV |
| `CU_fut_close.csv` | OHLCV |
| `EC_fut_close.csv` | OHLCV |
| `I_fut_close.csv` | OHLCV |
| `JM01_futures_ohlcv_*.csv` | OHLCV |
| `JM_fut_close.csv` | OHLCV |
| `LC_fut_close.csv` | OHLCV |
| `LH_fut_close.csv` | OHLCV |
| `M_fut_close.csv` | OHLCV |
| `NI_fut_close.csv` | OHLCV |
| `NR_fut_close.csv` | OHLCV |
| `P_fut_close.csv` | OHLCV |
| `PB_fut_close.csv` | OHLCV |
| `RB_fut_close.csv` | OHLCV |
| `RU_fut_close.csv` | OHLCV |
| `SA_fut_close.csv` | OHLCV |
| `SC_fut_close.csv` | OHLCV |
| `SN_fut_close.csv` | OHLCV |
| `TA_fut_close.csv` | OHLCV |
| `ZN_fut_close.csv` | OHLCV |

### LME_3M文件（列名已标准）
以下文件列名已符合规范（`date,symbol,latest,yesterday_settle,spread_diff`），无需修改：

| 文件 |
|------|
| `ZN_LME_3M.csv` |
| `PB_LME_3M.csv` |
| `SN_LME_3M.csv` |

### 其他宏观文件（无需修改）
| 文件 | 原因 |
|------|------|
| `CN_US_bond_yield_full.csv` | 多债券期限列（`cn_10y,cn_2y,cn_5y,us_10y,us_2y`），无单一price列 |
| `AG_SGE_silver_spot.csv` | 列名已是标准 `date,close,evening_close,morning_close` |

### 价差文件（未在任务范围内）
| 文件 | 原因 |
|------|------|
| `CU/LME_copper_cash_3m_spread.csv` | 未在任务描述中明确列出 |
| `NI/LME_nickel_cash_3m_spread.csv` | 未在任务描述中明确列出 |

---

## 备份文件

所有修改的文件均已创建 `.bak` 备份，路径为原文件同目录：

```
Brent_crude.csv.bak
USD_CNY_spot.csv.bak
CN_10Y_bond_yield.csv.bak
CN_10Y_bond_yield_v2.csv.bak
AU_AG_ratio_corrected.csv.bak
AU_AG_ratio_v2.csv.bak
usd_index.csv.bak
AU_SGE_SHFE_spread.csv.bak
JM10_jm_zc_ratio.csv.bak
```

---

## 编码说明

所有修改后的文件使用 `utf-8-sig`（UTF-8 with BOM），兼容 Windows Excel 打开。
