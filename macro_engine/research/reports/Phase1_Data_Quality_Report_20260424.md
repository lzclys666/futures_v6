# Phase 1 Data Quality Report

**Check time**: 2026-04-24 17:57:02

## Futures Price Data Validation

| Symbol | Rows | Status | Errors | Warnings |
|--------|------|--------|--------|----------|
| AG | 1523 | FAIL | Schema validation failed: column 'hold' not in dataframe. Columns in dataframe: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's'] | Time gaps >7 days: 13 instances |
| AL | 1523 | FAIL | Schema validation failed: column 'hold' not in dataframe. Columns in dataframe: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's'] | Time gaps >7 days: 13 instances |
| AO | 690 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 6 instances |
| AU | 1523 | FAIL | Schema validation failed: column 'hold' not in dataframe. Columns in dataframe: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's'] | Time gaps >7 days: 13 instances |
| BR | 663 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 6 instances |
| CU | 1523 | FAIL | Schema validation failed: column 'hold' not in dataframe. Columns in dataframe: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's'] | Time gaps >7 days: 13 instances |
| EC | 648 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 6 instances |
| I | 3043 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 23 instances; Zero volume: 1 rows |
| JM | 3175 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 25 instances; Zero volume: 3 rows |
| LC | 668 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 6 instances |
| LH | 1281 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 11 instances |
| M | 5185 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 43 instances; Zero volume: 1 rows |
| NI | 1522 | FAIL | Low > Close: 1 rows; Schema validation failed: column 'hold' not in dataframe. Columns in dataframe: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's'] | Time gaps >7 days: 13 instances |
| NR | 1624 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 14 instances |
| P | 4496 | FAIL | High < Close: 1 rows; Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 35 instances; Zero volume: 4 rows |
| PB | 3664 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 29 instances; Zero volume: 28 rows |
| RB | 4146 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 33 instances |
| RU | 5180 | FAIL | Low > Close: 1 rows; Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 44 instances; Zero volume: 4 rows |
| SA | 1546 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 13 instances |
| SC | 1960 | FAIL | Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 16 instances |
| SN | 2693 | FAIL | High < Close: 3 rows; Low > Close: 1 rows; Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 20 instances; Zero volume: 7 rows |
| TA | 4700 | FAIL | High < Close: 1 rows; Schema validation failed: expected series 'volume' to have type float64, got int64 | Time gaps >7 days: 38 instances |
| ZN | 1523 | FAIL | Schema validation failed: column 'hold' not in dataframe. Columns in dataframe: ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 's'] | Time gaps >7 days: 13 instances |

## Macro Factor Data Validation

| Factor | Rows | Columns | Date Range | Status |
|--------|------|---------|------------|--------|
| Gold/Silver Ratio | 1523 | date, au_ag_ratio_corrected | 2020-01-01 ~ 2026-04-15 | PASS |
| Brent Crude | 1638 | date, wti_spot_usd_bbl | 2020-01-02 ~ 2026-04-13 | PASS |
| CN/US Bond | 5674 | date, cn_10y, cn_2y, cn_5y, us_10y, us_2y | 2002-01-04 ~ 2026-04-17 | PASS |
| USD/CNY | 1723 | date, usd_cny, boc_banknote_buy, boc_cash_buy, boc_sell, pbc_mid | 2020-01-01 ~ 2026-04-21 | PASS |

## Summary

- Futures Price: PASS=0, WARN=0, FAIL=23
- Macro Factor: PASS=4/4
- Overall: FAIL
