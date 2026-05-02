"""
宏观打分引擎 · 历史回算脚本 V1.0
=================================
从 AKShare 拉取历史数据，计算 RU 品种的 7 个因子，
生成历史 CSV 文件（覆盖 macro_scoring_engine.py 所需的全部字段）。

使用方式：
    python scripts/macro_history_backfill.py [--start YYYYMMDD] [--end YYYYMMDD] [--symbol RU]

输出：
    C:\\futures_data\\macro_signals\\{SYMBOL}_macro_daily_{YYYYMMDD}.csv
"""

import csv
import time
import random
import math
import re
import json
import warnings
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# ---------------------------------------------------------------------------
# 依赖检查
# ---------------------------------------------------------------------------
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("[WARN] AKShare 未安装，将使用模拟数据")

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
CSV_BASE_DIR = Path(r"D:\futures_v6\macro_engine\output")  # 与 macro_scoring_engine.py 保持一致 (2026-04-22 修复)

# 回算日期范围（库存最早 2026-01-12）
DEFAULT_START = "20260112"
DEFAULT_END   = datetime.now().strftime("%Y%m%d")   # 今天

FACTOR_META = json.load(open(r"D:\futures_v6\config\factor_meta.json", encoding="utf-8"))


# ---------------------------------------------------------------------------
# 数据拉取层
# ---------------------------------------------------------------------------

def _fetch_spot_basis(date_str: str) -> Optional[dict]:
    """
    调用 futures_spot_price(date) 获取橡胶现货+近远月价差数据。
    date_str: YYYYMMDD 格式
    返回 dict:
        spot_price, near_contract_price, dominant_contract_price,
        near_basis, near_basis_rate, dom_basis_rate
    """
    try:
        df = ak.futures_spot_price(date_str)
        ru = df[df["symbol"] == "RU"]
        if ru.empty:
            return None
        row = ru.iloc[0]
        spot = float(row["spot_price"])
        near = float(row["near_contract_price"])
        dom  = float(row["dominant_contract_price"])
        if spot == 0:
            return None
        near_basis = near - spot
        near_basis_rate = near_basis / spot          # ≈ 展期成本率
        dom_basis_rate  = (dom - spot) / spot
        return {
            "spot_price":         spot,
            "near_contract_price": near,
            "dominant_contract_price": dom,
            "near_basis":         near_basis,
            "near_basis_rate":    near_basis_rate,
            "dom_basis_rate":     dom_basis_rate,
        }
    except Exception:
        return None


# 全局库存缓存（一次拉取全部，后续循环引用）
_INVENTORY_CACHE: Dict[str, float] = {}   # date_str(YYYY-MM-DD) → 库存值
_INVENTORY_FWD_CACHE: Dict[str, float] = {}  # 前向填充后的版本


def _load_inventory_cache() -> None:
    """一次性拉取橡胶库存全量数据，并做前向填充。"""
    global _INVENTORY_CACHE, _INVENTORY_FWD_CACHE
    try:
        df = ak.futures_inventory_em("\u6a61\u80f6")
        date_col = df.columns[0]
        inv_col  = df.columns[1]  # 库存数值（不是日变化量）
        for _, row in df.iterrows():
            d = str(row[date_col])[:10]   # YYYY-MM-DD
            try:
                val = float(row[inv_col])   # inv_col = df.columns[1] = 库存数值
                if not math.isnan(val) and not math.isinf(val):
                    _INVENTORY_CACHE[d] = val
            except (ValueError, TypeError):
                pass
        # 前向填充：用最后已知值填所有间隙
        dates_sorted = sorted(_INVENTORY_CACHE.keys())
        if dates_sorted:
            last_val = _INVENTORY_CACHE[dates_sorted[0]]
            for d_str in dates_sorted:
                last_val = _INVENTORY_CACHE[d_str]
            # 对所有日期做前向填充
            all_dates = list(_INVENTORY_CACHE.keys())
            last_val = None
            for d_str in sorted(all_dates):
                if d_str in _INVENTORY_CACHE:
                    last_val = _INVENTORY_CACHE[d_str]
                if last_val is not None:
                    _INVENTORY_FWD_CACHE[d_str] = last_val
        print(f"  [OK] 库存缓存已加载: {len(_INVENTORY_CACHE)} 条原始, {len(_INVENTORY_FWD_CACHE)} 条前向填充")
    except Exception as e:
        print(f"  [WARN] 库存接口失败: {e}")


def _fetch_inventory(date_str: str) -> Optional[float]:
    """
    从前向填充缓存获取指定日期的橡胶库存。
    date_str: YYYY-MM-DD 或 YYYYMMDD
    """
    d = date_str
    if len(d) == 8:
        d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return _INVENTORY_FWD_CACHE.get(d) or _INVENTORY_CACHE.get(d)


# 全局汇率缓存
_FX_CACHE: Dict[str, float] = {}   # date_str(YYYY-MM-DD) → USDCNH
_FX_LOADED: bool = False
# 汇率失败时的降级常数（2026年初 USDCNH ≈ 7.20）
_FX_FALLBACK: float = 7.20


def _load_fx_cache_with_retry(max_retries: int = 3, delay: float = 3.0) -> None:
    """
    汇率缓存加载（优化版）。
    优先使用 Frankfurter API（稳定），akshare forex_hist_em 作为 fallback。
    缺口日期（春节/国庆等无交易日）用前后最近交易日线性插值填充。
    """
    global _FX_CACHE, _FX_LOADED
    _FX_CACHE.clear()

    # ── 1. Frankfurter API（主数据源，稳定快速）──────────────────────────────
    try:
        import requests as _req
        _start = "2025-12-01"  # 多取一个月覆盖回填区间
        _end = datetime.now().strftime("%Y-%m-%d")
        _url = f"https://api.frankfurter.app/{_start}..{_end}"
        _r = _req.get(_url, params={"from": "USD", "to": "CNY"}, timeout=20)
        if _r.status_code == 200:
            _data = _r.json()
            _rates = _data.get("rates", {})
            _count = 0
            for _d, _v in _rates.items():
                if isinstance(_v, dict) and "CNY" in _v:
                    _FX_CACHE[_d] = float(_v["CNY"]); _count += 1
                elif isinstance(_v, (int, float)):
                    _FX_CACHE[_d] = float(_v); _count += 1
            if _count > 0:
                _FX_LOADED = True
                print(f"  [OK] Frankfurter汇率: {_count} 条, range {min(_FX_CACHE)} ~ {max(_FX_CACHE)}")
            # 插值填充缺口（春节/国庆等无交易日）
            _fill_gaps_linear(_FX_CACHE)
            print(f"  [OK] 插值后共 {len(_FX_CACHE)} 条")
        else:
            print(f"  [WARN] Frankfurter HTTP {_r.status_code}")
    except Exception as e1:
        print(f"  [WARN] Frankfurter异常: {e1}")

    # ── 2. akshare forex_hist_em（补充 Frankfurter 缺失的历史数据）──────────
    if not _FX_CACHE:
        for attempt in range(max_retries):
            try:
                df = ak.forex_hist_em("USDCNH")
                date_col = df.columns[0]
                price_col = next((c for c in df.columns
                                  if "close" in c.lower() or "收盘" in c or "现价" in c), df.columns[1])
                for _, row in df.iterrows():
                    d = str(row[date_col])[:10]
                    try:
                        val = float(row[price_col])
                        if not math.isnan(val) and 6.0 < val < 8.0:
                            _FX_CACHE[d] = val
                    except (ValueError, TypeError):
                        pass
                _FX_LOADED = bool(_FX_CACHE)
                print(f"  [OK] forex_hist_em: {len(_FX_CACHE)} 条 (fallback)")
                _fill_gaps_linear(_FX_CACHE)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  [RETRY] forex_hist_em ({attempt+1}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    print(f"  [WARN] forex_hist_em 连续失败: {e}")

    # ── 3. fx_spot_quote（仅补充今日，若 Frankfurter 已有今日则跳过）──────────
    _today = datetime.now().strftime("%Y-%m-%d")
    if _today not in _FX_CACHE:
        try:
            df_spot = ak.fx_spot_quote()
            usd_row = df_spot[df_spot.iloc[:, 0].str.contains("USD/CNY", na=False)]
            if not usd_row.empty:
                bid = float(usd_row.iloc[0, 1])
                ask = float(usd_row.iloc[0, 2])
                spot_rate = (bid + ask) / 2.0
                _FX_CACHE[_today] = spot_rate
                print(f"  [OK] fx_spot_quote今日: {_today}={spot_rate:.4f}")
        except Exception as e3:
            print(f"  [WARN] fx_spot_quote: {e3}")

    _FX_LOADED = bool(_FX_CACHE)
    if not _FX_CACHE:
        print(f"  [WARN] 所有汇率接口均失败，降级使用常数 {_FX_FALLBACK}")
        _FX_LOADED = False


def _fill_gaps_linear(cache: dict) -> None:
    """
    对缓存中缺失的日期（春节期间隔）进行线性插值。
    cache: {date_str: rate}，原地修改。
    """
    if len(cache) < 2:
        return
    sorted_dates = sorted(cache.keys())
    all_dates = []
    from datetime import datetime, timedelta
    start = datetime.strptime(sorted_dates[0], "%Y-%m-%d")
    end = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")
    cur = start
    while cur <= end:
        all_dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    gaps = [d for d in all_dates if d not in cache]
    if not gaps:
        return
    sorted_cache = sorted(cache.items())
    date_to_val = dict(sorted_cache)
    s_dates = sorted(date_to_val.keys())
    for g in gaps:
        # 找前后最近的有效日期
        prev_dates = [d for d in s_dates if d < g]
        next_dates = [d for d in s_dates if d > g]
        if prev_dates and next_dates:
            p = prev_dates[-1]; n = next_dates[0]
            pv = date_to_val[p]; nv = date_to_val[n]
            pd = (datetime.strptime(g, "%Y-%m-%d") - datetime.strptime(p, "%Y-%m-%d")).days
            nd = (datetime.strptime(n, "%Y-%m-%d") - datetime.strptime(g, "%Y-%m-%d")).days
            cache[g] = pv + (nv - pv) * pd / (pd + nd)
        elif prev_dates:
            cache[g] = date_to_val[prev_dates[-1]]
        elif next_dates:
            cache[g] = date_to_val[next_dates[0]]

def _load_fx_cache() -> None:
    _load_fx_cache_with_retry()


def _fetch_fx(date_str: str) -> Optional[float]:
    """
    从缓存获取 USDCNH 汇率（降级：缓存为空则返回常数）。
    date_str: YYYY-MM-DD 或 YYYYMMDD
    """
    d = date_str
    if len(d) == 8:
        d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    if _FX_LOADED and _FX_CACHE:
        return _FX_CACHE.get(d)
    # 降级：返回常数（方向正确，量级合理）
    return _FX_FALLBACK


# ---------------------------------------------------------------------------
# CU/AU/AG 数据缓存
# ---------------------------------------------------------------------------

# LME 铜库存（每日）
_LME_CU_CACHE: Dict[str, float] = {}  # date_str(YYYY-MM-DD) → 铜库存量
_LME_CU_LAST: Tuple[float, str] = (0.0, "")  # (最后值, 最后日期) 用于前向填充
_LME_CU_LOADED: bool = False
_LME_CU_CHG_HIST: List[float] = []   # 铜库存历史（用于日环比计算）

# ======== 中国能源指数缓存（日频）=======
_ENERGY_INDEX_CACHE: Dict[str, float] = {}
_ENERGY_INDEX_LOADED: bool = False

# 中国PMI（月度，前向填充到每日）
_PMI_CACHE: Dict[str, float] = {}      # date_str(YYYY-MM-DD) → PMI值
_PMI_LOADED: bool = False

# 美债收益率（每日）
_US10Y_CACHE: Dict[str, float] = {}   # date_str(YYYY-MM-DD) → 美10年收益率（bond_zh_us_rate，已失效）
_US10Y_2Y_CACHE: Dict[str, float] = {} # date_str(YYYY-MM-DD) → 美2年收益率
_US10Y_SINA_CACHE: Dict[str, float] = {}  # date_str(YYYY-MM-DD) → 美10年收益率（Sina补充）
_US10Y_SINA_LOADED: bool = False
_BOND_LOADED: bool = False

# 央行购金（每日）
_CB_GOLD_CACHE: Dict[str, float] = {}  # date_str(YYYY-MM-DD) → 黄金持仓(吨)
_CB_GOLD_LOADED: bool = False

# 工业增加值YoY（月度）
_IP_CACHE: Dict[str, float] = {}       # date_str(YYYY-MM-DD) → 工业增加值YoY
_IP_LOADED: bool = False

# 房地产指数YoY（月度）
_PROP_CACHE: Dict[str, float] = {}      # date_str(YYYY-MM-DD) → 房地产指数
_PROP_LOADED: bool = False

# 央行购金日变化率历史（用于 RSI 计算）
_CB_GOLD_CHG_HIST: List[Tuple[str, float]] = []  # [(date_str, daily_pct_chg), ...]
_RSI_PERIOD: int = 26  # RSI 周期（26天 ≈ 5周，周频数据）

# 黄金期货日变化率历史（用于 AU_GOLD_RSI，替代 CB 黄金 RSI）
_GOLD_FUTURES_CHG_HIST: List[float] = []  # 日变化率（小数），每天一个值

# 上海期货日线缓存（用于 AG 因子）
_GOLD_FUTURES_CACHE: Dict[str, float] = {}   # date_str → 黄金期货收盘价(CNY/g)
_SILVER_FUTURES_CACHE: Dict[str, float] = {}  # date_str → 白银期货收盘价(CNY/kg)
_CU_FUTURES_CACHE: Dict[str, float] = {}      # date_str → 铜期货收盘价(CNY/ton)
_FUTURES_LOADED: bool = False


def _to_iso(date_str: str) -> str:
    """将 YYYYMMDD 转换为 YYYY-MM-DD"""
    if len(date_str) == 8 and date_str.replace("-", "").isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str[:10] if len(date_str) >= 10 else date_str


def _load_lme_cu_cache() -> None:
    """加载 LME 铜库存数据（每日），缓存原始数据"""
    global _LME_CU_CACHE, _LME_CU_LAST, _LME_CU_LOADED
    try:
        df = ak.macro_euro_lme_stock()
        date_col = df.columns[0]
        cu_col = "铜-库存"
        last_val, last_date = None, None
        for _, row in df.iterrows():
            d = str(row[date_col])[:10]
            try:
                val = float(row[cu_col])
                if not math.isnan(val) and val > 0:
                    _LME_CU_CACHE[d] = val
                    last_val, last_date = val, d
            except (ValueError, TypeError):
                pass
        if last_val is not None:
            _LME_CU_LAST = (last_val, last_date)
        _LME_CU_LOADED = True
        print(f"  [OK] LME铜库存缓存已加载: {len(_LME_CU_CACHE)} 条原始, 最后: {last_date}={last_val}")
    except Exception as e:
        print(f"  [WARN] LME铜库存接口失败: {e}")


def _load_energy_index_cache() -> None:
    """加载中国能源指数（日频），用于替代工业增加值常数"""
    global _ENERGY_INDEX_CACHE, _ENERGY_INDEX_LOADED
    try:
        df = ak.macro_china_energy_index()
        date_col = df.columns[0]
        idx_col = df.columns[1]
        for _, row in df.iterrows():
            d = str(row[date_col])[:10]
            try:
                val = float(row[idx_col])
                if 500 < val < 2000:
                    _ENERGY_INDEX_CACHE[d] = val
            except (ValueError, TypeError):
                pass
        _ENERGY_INDEX_LOADED = True
        print(f"  [OK] 中国能源指数已加载: {len(_ENERGY_INDEX_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 能源指数加载失败: {e}")
        _ENERGY_INDEX_LOADED = False


def _load_pmi_cache() -> None:
    """加载中国PMI（月度）"""
    global _PMI_CACHE, _PMI_LOADED
    try:
        import re
        df = ak.macro_china_pmi()
        date_col = df.columns[0]
        pmi_col = "制造业-指数"
        for _, row in df.iterrows():
            d = str(row[date_col])
            # 格式: "2026年03月份" → "2026-03-01"
            m = re.match(r'(\d{4})年(\d+)月份', d)
            if m:
                year, month = m.group(1), m.group(2).zfill(2)
                d_iso = f"{year}-{month}-01"
            else:
                d_iso = d.replace("年", "-").replace("月", "-").replace("日", "")[:10]
            try:
                val = float(row[pmi_col])
                if not math.isnan(val):
                    _PMI_CACHE[d_iso] = val
            except (ValueError, TypeError):
                pass
        _PMI_LOADED = True
        print(f"  [OK] 中国PMI缓存已加载: {len(_PMI_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 中国PMI接口失败: {e}")


def _load_bond_cache() -> None:
    """加载中美债券收益率（每日），使用 pandas 向量化操作加速"""
    global _US10Y_CACHE, _US10Y_2Y_CACHE, _BOND_LOADED
    try:
        df = ak.bond_zh_us_rate()
        if HAS_PANDAS:
            df = df.copy()
            df["日期"] = df.iloc[:, 0].astype(str).str[:10]
            # 智能查找10Y列
            cols = df.columns.tolist()
            us10y_col = next((c for c in cols if "10" in str(c) and ("美国" in str(c) or "美" in str(c) or "年" in str(c))), None)
            us2y_col = next((c for c in cols if "2" in str(c) and ("美国" in str(c) or "美" in str(c) or "年" in str(c))), None)
            if us10y_col:
                _US10Y_CACHE = dict(zip(df["日期"], pd.to_numeric(df[us10y_col], errors="coerce")))
                _US10Y_CACHE = {k: v for k, v in _US10Y_CACHE.items() if not math.isnan(v)}
            if us2y_col:
                _US10Y_2Y_CACHE = dict(zip(df["日期"], pd.to_numeric(df[us2y_col], errors="coerce")))
                _US10Y_2Y_CACHE = {k: v for k, v in _US10Y_2Y_CACHE.items() if not math.isnan(v)}
        else:
            # 降级：逐行
            date_col = df.columns[0]
            cols = df.columns.tolist()
            us10y_col = next((c for c in cols if "10" in str(c) and ("美国" in str(c) or "美" in str(c))), None)
            us2y_col = next((c for c in cols if "2" in str(c) and ("美国" in str(c) or "美" in str(c))), None)
            for _, row in df.iterrows():
                d = str(row[date_col])[:10]
                try:
                    v10 = float(row[us10y_col]) if us10y_col and us10y_col in df.columns else None
                    v2 = float(row[us2y_col]) if us2y_col and us2y_col in df.columns else None
                    if v10 is not None and not math.isnan(v10):
                        _US10Y_CACHE[d] = v10
                    if v2 is not None and not math.isnan(v2):
                        _US10Y_2Y_CACHE[d] = v2
                except (ValueError, TypeError):
                    pass
        _BOND_LOADED = True
        print(f"  [OK] 美债10Y缓存: {len(_US10Y_CACHE)} 条, 2Y缓存: {len(_US10Y_2Y_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 美债接口失败: {e}")


def _load_cb_gold_cache() -> None:
    """加载全球央行购金数据（每日，简单前向填充）"""
    global _CB_GOLD_CACHE, _CB_GOLD_LOADED
    try:
        df = ak.macro_cons_gold()
        # 提取黄金数据
        gold = df[df["商品"] == "黄金"].copy()
        gold["日期_str"] = gold["日期"].astype(str).str[:10]
        gold = gold.sort_values("日期_str")
        # 简单前向填充：用最近历史值填充缺失日期
        last_val = None
        for _, row in gold.iterrows():
            d = row["日期_str"]
            try:
                val = float(row["总库存"])
                if not math.isnan(val) and val > 0:
                    last_val = val
                    _CB_GOLD_CACHE[d] = val
            except (ValueError, TypeError):
                pass
        _CB_GOLD_LOADED = True
        print(f"  [OK] 央行购金缓存已加载: {len(_CB_GOLD_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 央行购金接口失败: {e}")


def _load_ip_cache() -> None:
    """加载中国工业增加值YoY（月度）"""
    global _IP_CACHE, _IP_LOADED
    try:
        df = ak.macro_china_industrial_production_yoy()
        # 取第一条记录（整体工业增加值）
        date_col = df.columns[1]  # "日期"
        val_col = "今值"
        for _, row in df.iterrows():
            d = str(row[date_col])[:10]
            try:
                val = float(row[val_col])
                if not math.isnan(val):
                    _IP_CACHE[d] = val
            except (ValueError, TypeError):
                pass
        _IP_LOADED = True
        print(f"  [OK] 工业增加值缓存已加载: {len(_IP_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 工业增加值接口失败: {e}")


def _load_property_cache() -> None:
    """加载中国房地产指数（月度）"""
    global _PROP_CACHE, _PROP_LOADED
    try:
        df = ak.macro_china_real_estate()
        date_col = df.columns[0]
        val_col = "最新值"
        for _, row in df.iterrows():
            d = str(row[date_col])[:10]
            try:
                val = float(row[val_col])
                if not math.isnan(val) and val > 0:
                    _PROP_CACHE[d] = val
            except (ValueError, TypeError):
                pass
        _PROP_LOADED = True
        print(f"  [OK] 房地产指数缓存已加载: {len(_PROP_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 房地产指数接口失败: {e}")


def _load_futures_cache() -> None:
    """加载上海期货日线数据：黄金(au0)、白银(ag0)、铜(cu0)"""
    global _GOLD_FUTURES_CACHE, _SILVER_FUTURES_CACHE, _CU_FUTURES_CACHE, _FUTURES_LOADED
    if _FUTURES_LOADED:
        return
    _FUTURES_LOADED = True

    try:
        df_gold = ak.futures_zh_daily_sina(symbol='au0')
        df_gold = df_gold.copy()
        df_gold['date'] = pd.to_datetime(df_gold['date']).dt.strftime('%Y-%m-%d')
        df_gold = df_gold.dropna(subset=['close'])
        _GOLD_FUTURES_CACHE = dict(zip(df_gold['date'], df_gold['close'].astype(float)))
        print(f"  [OK] 黄金期货(au0)缓存: {len(_GOLD_FUTURES_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 黄金期货接口失败: {e}")

    try:
        df_silver = ak.futures_zh_daily_sina(symbol='ag0')
        df_silver = df_silver.copy()
        df_silver['date'] = pd.to_datetime(df_silver['date']).dt.strftime('%Y-%m-%d')
        df_silver = df_silver.dropna(subset=['close'])
        _SILVER_FUTURES_CACHE = dict(zip(df_silver['date'], df_silver['close'].astype(float)))
        print(f"  [OK] 白银期货(ag0)缓存: {len(_SILVER_FUTURES_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 白银期货接口失败: {e}")

    try:
        df_cu = ak.futures_zh_daily_sina(symbol='cu0')
        df_cu = df_cu.copy()
        df_cu['date'] = pd.to_datetime(df_cu['date']).dt.strftime('%Y-%m-%d')
        df_cu = df_cu.dropna(subset=['close'])
        _CU_FUTURES_CACHE = dict(zip(df_cu['date'], df_cu['close'].astype(float)))
        print(f"  [OK] 铜期货(cu0)缓存: {len(_CU_FUTURES_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 铜期货接口失败: {e}")


def _load_us10y_sina_cache() -> None:
    """加载美债10Y收益率（Sina，bond_gb_us_sina）备选数据源
    主数据源 bond_zh_us_rate（akshare，1990年至今）优先；
    Sina 作为备选（数据范围2022年起，1000条，历史覆盖较短）。
    """
    global _US10Y_SINA_CACHE, _US10Y_SINA_LOADED
    try:
        df = ak.bond_gb_us_sina()
        date_col = df.columns[0]
        close_col = "close"
        for _, row in df.iterrows():
            d = str(row[date_col])[:10]
            try:
                v = float(row[close_col])
                if 0 < v < 20:  # 合理区间过滤
                    _US10Y_SINA_CACHE[d] = v
            except (ValueError, TypeError):
                pass
        _US10Y_SINA_LOADED = True
        print(f"  [OK] 美债10Y(Sina)缓存: {len(_US10Y_SINA_CACHE)} 条")
    except Exception as e:
        print(f"  [WARN] 美债10Y(Sina)加载失败: {e}")
        _US10Y_SINA_LOADED = False

def _load_all_caches() -> None:
    """一次性加载所有 CU/AU/AG 缓存"""
    _load_lme_cu_cache()
    _load_pmi_cache()
    _load_bond_cache()
    _load_us10y_sina_cache()  # 补充Sina美债数据
    _load_cb_gold_cache()
    _load_ip_cache()
    _load_property_cache()
    _load_futures_cache()
    _load_energy_index_cache()


def _get_monthly_filled(date_iso: str, cache: Dict[str, float]) -> Optional[float]:
    """
    从月度缓存获取当日值（前向填充）。
    逻辑：date_iso 落在哪个月，就用那个月1日的值；否则向前逐月找最近的月份。
    date_iso: YYYY-MM-DD
    返回值或 None（所有月都找不到时用缓存中最新的值兜底）
    """
    if date_iso in cache:
        return cache[date_iso]
    d = datetime.strptime(date_iso, "%Y-%m-%d")
    # 向前逐月找：先试当月1日，再试上月1日，再上月...
    for offset in range(13):
        check_d = d.replace(day=1)
        if offset > 0:
            # 退到上个月
            month = check_d.month - offset
            year = check_d.year
            while month <= 0:
                month += 12
                year -= 1
            check_d = check_d.replace(year=year, month=month)
        check_str = check_d.strftime("%Y-%m-%d")
        if check_str in cache:
            return cache[check_str]
    # 兜底：回测区间外，用最新值
    if cache:
        latest = sorted(cache.keys())[-1]
        return cache[latest]
    return None


# ---------------------------------------------------------------------------
# RSI 计算（用于 AU_GOLD_RSI）
# ---------------------------------------------------------------------------

def _compute_rsi_from_chg_hist(chg_hist: List[float], period: int = 26) -> Optional[float]:
    """
    给定日变化率序列，计算 RSI。
    chg_hist: 日变化率（小数，如 0.01 表示 1%）
    period: RSI 周期
    """
    if len(chg_hist) < period:
        return None
    gains = [max(0.0, c) for c in chg_hist[-period:]]
    losses = [abs(min(0.0, c)) for c in chg_hist[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ---------------------------------------------------------------------------
# 历史数据拉取（每日）
# ---------------------------------------------------------------------------

def fetch_daily_data(symbol: str, date_str: str) -> dict:
    """
    构建指定日期的 raw_data dict。
    date_str: YYYYMMDD
    """
    d_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # ====== RU 品种 ======
    if symbol == "RU":
        spot = None
        try:
            spot_df = ak.futures_spot_price(date_str)
            ru_row = spot_df[spot_df["symbol"] == "RU"]
            if not ru_row.empty:
                row = ru_row.iloc[0]
                sp = float(row["spot_price"])
                near = float(row["near_contract_price"])
                dom  = float(row["dominant_contract_price"])
                if sp > 0:
                    near_basis = near - sp
                    near_basis_rate = near_basis / sp
                    dom_basis_rate  = (dom - sp) / sp
                    spot = {
                        "spot_price": sp,
                        "near_contract_price": near,
                        "dominant_contract_price": dom,
                        "near_basis": near_basis,
                        "near_basis_rate": near_basis_rate,
                        "dom_basis_rate": dom_basis_rate,
                    }
        except Exception:
            pass

        inv = _fetch_inventory(d_iso) or 0.0
        fx  = _fetch_fx(d_iso) or _FX_FALLBACK
        return {
            "spot_price":      spot["spot_price"]         if spot else None,
            "near_basis_rate": spot["near_basis_rate"]    if spot else None,
            "dom_basis_rate":  spot["dom_basis_rate"]    if spot else None,
            "inventory":       inv,
            "usdcnh":          fx,
        }

    # ====== CU 品种 ======
    if symbol == "CU":
        # LME铜库存（每日，含前向填充：从最近历史值填充缺失日）
        cu_inv = _LME_CU_CACHE.get(d_iso)
        if cu_inv is None:
            # 前向填充：找最近的历史日期
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            found_val = None
            for delta in range(1, 30):  # 最多向前找30天
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _LME_CU_CACHE:
                    found_val = _LME_CU_CACHE[check]
                    break
            cu_inv = found_val if found_val is not None else 0.0

        # 中国PMI（月度前向填充）
        pmi_val = _get_monthly_filled(d_iso, _PMI_CACHE)

        # 美债收益率（每日）
        us10y = _US10Y_CACHE.get(d_iso)
        us2y  = _US10Y_2Y_CACHE.get(d_iso)
        us10y_yoy = None
        if us10y is not None and us2y is not None:
            us10y_yoy = (us10y - us2y) / us2y * 100  # 10Y-2Y利差

        # 房地产指数（月度前向填充）
        prop_val = _get_monthly_filled(d_iso, _PROP_CACHE)

        # 工业增加值YoY（月度前向填充）
        ip_val = _get_monthly_filled(d_iso, _IP_CACHE)

        # 汇率：降级常数
        fx = _fetch_fx(d_iso) or _FX_FALLBACK

        return {
            "lme_cu_inventory": cu_inv,
            "china_pmi":        pmi_val,
            "usdcny":           fx,
            "us10y_yoy":        us10y_yoy,
            "property_val":     prop_val,
            "industrial_ip":     ip_val,
        }

    # ====== AU 品种 ======
    if symbol == "AU":
        # 美债收益率（每日，含前向填充）
        # 主数据源：bond_zh_us_rate（akshare，1990年至今，8846条）；
        # 备选：Sina（bond_gb_us_sina，2022年起，1000条，数据范围更窄）；
        # 最终兜底：常量 None（宏观中性）
        us10y = _US10Y_CACHE.get(d_iso)
        if us10y is None:
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            for delta in range(1, 15):
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _US10Y_CACHE:
                    us10y = _US10Y_CACHE[check]
                    break
            # 备选：Sina（akshare历史不足时启用）
            if us10y is None:
                us10y = _US10Y_SINA_CACHE.get(d_iso)
                if us10y is None:
                    for delta in range(1, 15):
                        check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                        if check in _US10Y_SINA_CACHE:
                            us10y = _US10Y_SINA_CACHE[check]
                            break
        us2y  = _US10Y_2Y_CACHE.get(d_iso)
        if us2y is None:
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            for delta in range(1, 15):
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _US10Y_2Y_CACHE:
                    us2y = _US10Y_2Y_CACHE[check]
                    break
        us10y_spread = (us10y - us2y) if (us10y and us2y) else None

        # 汇率：降级常数
        fx = _fetch_fx(d_iso) or _FX_FALLBACK

        # 央行购金（含前向填充：找最近历史值）
        cb_gold = _CB_GOLD_CACHE.get(d_iso)
        if cb_gold is None:
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            for delta in range(1, 15):
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _CB_GOLD_CACHE:
                    cb_gold = _CB_GOLD_CACHE[check]
                    break

        # ====== 黄金期货 RSI（AU_GOLD_RSI）======
        # 使用 au0 黄金期货日频数据（4451条），替代 CB 黄金周频数据
        gold_close = _GOLD_FUTURES_CACHE.get(d_iso)
        gold_chg_rate = 0.0
        if _GOLD_FUTURES_CHG_HIST:
            prev_gold = _GOLD_FUTURES_CACHE.get(
                (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            )
            if prev_gold and prev_gold > 0 and gold_close is not None:
                gold_chg_rate = (gold_close - prev_gold) / prev_gold
                gold_chg_rate = max(-0.1, min(0.1, gold_chg_rate))
        if gold_close is not None:
            _GOLD_FUTURES_CHG_HIST.append(gold_chg_rate)

        # 计算 AU_GOLD_RSI（26天 RSI，从黄金期货日变化率）
        au_gold_rsi = _compute_rsi_from_chg_hist(_GOLD_FUTURES_CHG_HIST, period=_RSI_PERIOD)

        # CB 黄金变化率（仍用于 CB_GOLD 因子，但不用于 RSI）
        cb_gold_chg_rate = 0.0
        if _CB_GOLD_CHG_HIST:
            prev_cb_gold = _CB_GOLD_CHG_HIST[-1][1]
            if prev_cb_gold and prev_cb_gold > 0 and cb_gold is not None:
                cb_gold_chg_rate = (cb_gold - prev_cb_gold) / prev_cb_gold
                cb_gold_chg_rate = max(-0.5, min(0.5, cb_gold_chg_rate))
        if cb_gold is not None:
            _CB_GOLD_CHG_HIST.append((d_iso, cb_gold))

        return {
            "us10y_real_rate":   us10y,
            "usdcny":             fx,
            "cb_gold_chg":       cb_gold,        # 绝对持仓量（compute_factor_raw 算日环比）
            "cb_gold_chg_rate":  cb_gold_chg_rate,  # 日环比（用于 RSI）
            "au_gold_rsi":       au_gold_rsi,    # RSI（直接是 0-100）
            "us10y_spread":      us10y_spread,
            "us10y_nominal":     us10y,
        }

    # ====== AG 品种 ======
    if symbol == "AG":
        # LME铜库存（每日，含前向填充）
        cu_inv = _LME_CU_CACHE.get(d_iso)
        if cu_inv is None:
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            for delta in range(1, 30):
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _LME_CU_CACHE:
                    cu_inv = _LME_CU_CACHE[check]
                    break
            if cu_inv is None:
                cu_inv = 0.0

        # 中国PMI（月度前向填充）
        pmi_val = _get_monthly_filled(d_iso, _PMI_CACHE)

        # 工业增加值YoY（月度前向填充）
        ip_val = _get_monthly_filled(d_iso, _IP_CACHE)

        # 中国能源指数（日频前向填充）
        energy_val = _ENERGY_INDEX_CACHE.get(d_iso)
        if energy_val is None:
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            for delta in range(1, 15):
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _ENERGY_INDEX_CACHE:
                    energy_val = _ENERGY_INDEX_CACHE[check]
                    break

        # 汇率：降级常数
        fx = _fetch_fx(d_iso) or _FX_FALLBACK

        # 央行购金（含前向填充）
        cb_gold = _CB_GOLD_CACHE.get(d_iso)
        if cb_gold is None:
            d_dt = datetime.strptime(d_iso, "%Y-%m-%d")
            for delta in range(1, 15):
                check = (d_dt - timedelta(days=delta)).strftime("%Y-%m-%d")
                if check in _CB_GOLD_CACHE:
                    cb_gold = _CB_GOLD_CACHE[check]
                    break

        # 金银比因子（金银比 = 黄金/白银价格，代理：黄金日环比变化率）
        # _CB_GOLD_CHG_HIST: [(date, gold_value), ...]（由 AU/AG fetch 共同维护）
        ag_au_ag_ratio = None
        if len(_CB_GOLD_CHG_HIST) >= 2:
            prev_cb = _CB_GOLD_CHG_HIST[-2][1]  # -2 = 前一天的绝对持仓量
            if prev_cb and prev_cb > 0 and cb_gold is not None:
                ag_au_ag_ratio = (cb_gold - prev_cb) / prev_cb
                ag_au_ag_ratio = max(-0.5, min(0.5, ag_au_ag_ratio))
        # AG 独立维护 _CB_GOLD_CHG_HIST（AU fetch 已维护，AG backfill 独立运行需自行填充）
        if cb_gold is not None:
            _CB_GOLD_CHG_HIST.append((d_iso, cb_gold))

        # 铜库存日环比（用于 AG_CU_PRICE 的 lme_cu_inventory_inv 代理）
        cu_inv_chg_rate = None
        if len(_LME_CU_CHG_HIST) >= 1:
            prev_cu = _LME_CU_CHG_HIST[-1]
            if prev_cu and prev_cu > 0 and cu_inv is not None:
                cu_inv_chg_rate = (cu_inv - prev_cu) / prev_cu
                cu_inv_chg_rate = max(-0.5, min(0.5, cu_inv_chg_rate))
        if cu_inv is not None and cu_inv > 0:
            _LME_CU_CHG_HIST.append(cu_inv)

        # 浠垮叡璁??涓?10澶╃殑鏃ユ湡鏌ヨ礋鍊?
        gold_close = None
        for delta in range(0, 10):
            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")
            if check in _GOLD_FUTURES_CACHE:
                gold_close = _GOLD_FUTURES_CACHE[check]
                break
        silver_close = None
        for delta in range(0, 10):
            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")
            if check in _SILVER_FUTURES_CACHE:
                silver_close = _SILVER_FUTURES_CACHE[check]
                break
        cu_close = None
        for delta in range(0, 10):
            check = (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=delta)).strftime("%Y-%m-%d")
            if check in _CU_FUTURES_CACHE:
                cu_close = _CU_FUTURES_CACHE[check]
                break

        # 鏍规嵁鐪熷疄鏈哄惎鍜岄噾铔?璁′换涓轰互涓嬫牴鎹?
        # ag0: CNY/kg, au0: CNY/g * 31.1035 = CNY/kg
        ag_au_real_ratio = None
        if gold_close is not None and silver_close is not None and gold_close > 0:
            gold_kg = gold_close * 31.1035
            ag_au_real_ratio = silver_close / gold_kg

        return {
            "lme_cu_inventory":   cu_inv,
            "lme_cu_chg_rate":   cu_inv_chg_rate,
            "china_pmi":          pmi_val,
            "usdcny":             fx,
            "industrial_ip":     ip_val,
            "energy_index":      energy_val,
            "cb_gold_chg":       cb_gold,
            "gold_futures_close": gold_close,
            "silver_futures_close": silver_close,
            "cu_futures_close":   cu_close,
            "ag_au_real_ratio":  ag_au_real_ratio,
        }

    # 返回空字典

    return {}


# ---------------------------------------------------------------------------
# 因子计算层
# ---------------------------------------------------------------------------

def compute_factor_raw(factor_meta: dict, raw_data: dict, prev_raw: dict) -> Optional[float]:
    """
    根据 proxy 类型计算因子的 raw_value。
    prev_raw: 前一天的 raw_data（用于计算变化率）
    注意：raw_data 中 inventory 为 None 表示该日无数据，用前向填充值。
    """
    proxy = factor_meta["proxy"]

    if proxy == "near_basis_rate":
        v = raw_data.get("near_basis_rate")
        if v is None:
            return None
        # 展期成本率为负（近月贴水）时 → raw_value 为正（利好）
        # 展期成本率为正（近月升水）时 → raw_value 为负（利空）
        return -v   # 取负：近月贴水 → 正收益

    elif proxy == "inventory_chg_rate":
        # raw_data["inventory"] 已经是前向填充过的值
        inv  = raw_data.get("inventory")
        pinv = prev_raw.get("inventory") if prev_raw else None
        if inv is None or pinv is None or pinv == 0:
            return None
        chg = (inv - pinv) / pinv
        # 限制极端值
        return max(-0.5, min(0.5, chg))

    elif proxy == "spot_price_return":
        sp  = raw_data.get("spot_price")
        psp = prev_raw.get("spot_price") if prev_raw else None
        if sp is None or psp is None or psp == 0:
            return None
        ret = (sp - psp) / psp
        # 限制极端值
        return max(-0.2, min(0.2, ret))

    elif proxy == "inventory":
        v = raw_data.get("inventory")
        return v if v is not None else None

    elif proxy == "spot_price":
        v = raw_data.get("spot_price")
        return v if v is not None else None

    elif proxy == "usdcny":
        v = raw_data.get("usdcnh")   # USDCNH 代理 USDCNY
        if v is None:
            return None
        return v

    elif proxy == "roll_yield":
        # 合并到 TS_ROLL_YIELD，此处返回 0
        v = raw_data.get("near_basis_rate")
        return -v if v is not None else 0.0

    # ======== CU 因子 proxy ========

    elif proxy == "lme_cu_inventory":
        # 铜库存：返回绝对量（后续归一化时高低代表库存高低）
        v = raw_data.get("lme_cu_inventory")
        return v if v is not None else None

    elif proxy == "china_pmi_monthly":
        # PMI：返回月度PMI（前向填充的日频值）
        v = raw_data.get("china_pmi")
        return v if v is not None else None

    elif proxy == "usdcny_proxy":
        # USDCNY 代理（汇率）：返回汇率值
        v = raw_data.get("usdcny")
        return v if v is not None else None

    elif proxy == "usdcny_proxy_momentum":
        # USDCNY 变化率（美元动能）
        fx  = raw_data.get("usdcny")
        pfx = prev_raw.get("usdcny") if prev_raw else None
        if fx is None or pfx is None or pfx == 0:
            return None
        return (fx - pfx) / pfx

    elif proxy == "us10y_china_yoy":
        # 美中利差YoY（REER替代）：返回10Y-2Y利差值
        v = raw_data.get("us10y_yoy")
        return v if v is not None else None

    elif proxy == "property_yoy":
        # 房地产指数YoY（前向填充）
        v = raw_data.get("property_val")
        return v if v is not None else None

    elif proxy == "industrial_ip_yoy":
        # 工业增加值YoY（前向填充）：优先用能源指数，其次用月度IP
        v = raw_data.get("energy_index") or raw_data.get("industrial_ip")
        return v if v is not None else None

    elif proxy == "us10y_yield_chg":
        # 美10年收益率变化（风险偏好代理）
        us10y  = raw_data.get("us10y_yoy")
        return us10y  # 已经是利差值，直接返回

    # ======== AU 因子 proxy ========

    elif proxy == "us10y_real_rate":
        # 美国实际利率：使用美10年收益率作为实际利率代理
        v = raw_data.get("us10y_real_rate")
        return v if v is not None else None

    elif proxy == "cb_gold_chg":
        # 央行购金变化率（日环比）：用 fetch 返回的日环比字段
        chg_rate = raw_data.get("cb_gold_chg_rate")
        if chg_rate is not None:
            return chg_rate
        # 降级：手动计算
        cb  = raw_data.get("cb_gold_chg")
        pcb = prev_raw.get("cb_gold_chg") if prev_raw else None
        if cb is None:
            return None
        if pcb is None or pcb == 0:
            return 0.0
        chg = (cb - pcb) / pcb
        return max(-0.5, min(0.5, chg))

    elif proxy == "au_gold_rsi":
        # 黄金 RSI（0-100）：fetch 已计算完毕，直接返回
        v = raw_data.get("au_gold_rsi")
        return v  # 0-100 或 None

    elif proxy == "us10y_spread_chg":
        # 美10Y-2Y利差变化率（VIX替代）
        spread = raw_data.get("us10y_spread")
        pspread = prev_raw.get("us10y_spread") if prev_raw else None
        if spread is None:
            return None
        if pspread is None or pspread == 0:
            return 0.0
        chg = (spread - pspread) / abs(pspread)
        return max(-0.5, min(0.5, chg))

    elif proxy == "cb_gold_holding":
        # 央行黄金持仓绝对量
        v = raw_data.get("cb_gold_chg")
        return v if v is not None else None

    elif proxy == "us10y_nominal_rate":
        # 美10年名义利率（通胀预期代理）
        v = raw_data.get("us10y_nominal")
        return v if v is not None else None

    # ======== AG 因子 proxy ========

    elif proxy == "lme_cu_inventory_inv":
        cu_price = raw_data.get("cu_futures_close")
        if cu_price is not None:
            return cu_price
        chg = raw_data.get("lme_cu_chg_rate")
        if chg is not None:
            return -chg
        v = raw_data.get("lme_cu_inventory")
        if v is None:
            return None
        return -(v / 100000.0)

    elif proxy == "ag_au_ag_ratio":
        v = raw_data.get("ag_au_real_ratio")
        return v
    elif proxy == "ag_au_ag_ratio":
        # 金银比因子：日环比变化率
        v = raw_data.get("ag_au_ag_ratio")
        return v  # 已是小数（-0.5~0.5）或 None

    return None


ROLLING_WINDOW = 60  # 固定窗口大小（交易日）
VOLATILITY_THRESHOLD = 1e-9  # MAD 低于此值视为低波动，返回 0


def normalize_mad(value: float, series: List[float]) -> float:
    """
    MAD (Median Absolute Deviation) 标准化。
    x' = (x - median) / (1.483 * MAD)
    使用 rolling window（仅最近 ROLLING_WINDOW 个数据点）

    当 MAD < VOLATILITY_THRESHOLD 时（低波动序列，如前向填充的月度数据），
    fallback 到标准差 z-score，避免归一化结果全为 0。
    """
    if len(series) < 3:
        return 0.0
    median = sorted(series)[len(series) // 2]
    mad = sorted([abs(x - median) for x in series])[len(series) // 2]
    if mad >= VOLATILITY_THRESHOLD:
        return (value - median) / (1.483 * mad)

    # Fallback：标准差 z-score（处理低波动 level 指标，如前向填充的 PMI/IP）
    mean = sum(series) / len(series)
    variance = sum((x - mean) ** 2 for x in series) / len(series)
    std = variance ** 0.5
    if std < VOLATILITY_THRESHOLD:
        # 序列几乎无变化（全是同一常数），使用 (value - median) / reference_range 方式
        ref_range = max(abs(max(series) - median), abs(median - min(series)), 1.0)
        return (value - median) / ref_range
    return (value - mean) / std


# ---------------------------------------------------------------------------
# expanding window 归一化
# ---------------------------------------------------------------------------

def normalize_all(raw_series: List[Optional[float]]) -> List[float]:
    """
    对 raw_value 序列做 rolling window MAD 归一化（最近60交易日）。
    跳过 None 值（返回 0.0）。
    返回归一化后的 list，长度与输入一致。
    """
    result = []
    window = []  # rolling window buffer
    for v in raw_series:
        if v is None:
            result.append(0.0)
        else:
            window.append(v)
            if len(window) > ROLLING_WINDOW:
                window.pop(0)  # 保持窗口大小固定
            norm = normalize_mad(v, window)   # rolling: 仅最近 window 个值
            result.append(math.tanh(norm * 0.5))  # tanh 压缩到 [-1, 1]
    return result


# ---------------------------------------------------------------------------
# CSV 写入
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(symbol: str, date_str: str, composite_score: float,
               direction: str, factors: List[dict],
               updated_at: str) -> Path:
    """
    写入单个品种单日 CSV 文件。
    date_str: YYYYMMDD
    返回写入的 Path。
    """
    p = CSV_BASE_DIR / f"{symbol}_macro_daily_{date_str}.csv"
    ensure_dir(p)

    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # SUMMARY 行
        writer.writerow([
            "symbol", "date", "row_type", "composite_score", "direction",
            "factor_count", "updated_at", "engine_version",
            "factor_code", "factor_name", "raw_value",
            "normalized_score", "weight", "contribution",
            "factor_direction", "ic_value",
        ])
        writer.writerow([
            symbol, f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
            "SUMMARY", round(composite_score, 4), direction,
            len(factors), updated_at, "backfill_v1.0",
            "", "", "", "", "", "", "", "",
        ])
        # FACTOR 行
        for fac in factors:
            raw_v = fac.get("raw_value")
            # 防 nan/inf 写入 CSV
            if raw_v is None or math.isnan(raw_v) or math.isinf(raw_v):
                raw_v_str = ""
            else:
                raw_v_str = str(round(float(raw_v), 6))
            ic_v = fac.get("ic_value")
            if ic_v is None or math.isnan(ic_v) or math.isinf(ic_v):
                ic_v_str = ""
            else:
                ic_v_str = str(round(float(ic_v), 4))
            writer.writerow([
                symbol, f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
                "FACTOR", round(composite_score, 4), direction,
                len(factors), updated_at, "backfill_v1.0",
                fac["factor_code"],
                fac["factor_name"],
                raw_v_str,
                round(fac["normalized_score"], 4),
                fac["weight"],
                round(fac["contribution"], 6),
                fac["factor_direction"],
                ic_v_str,
            ])

    return p


# ---------------------------------------------------------------------------
# 主回算逻辑
# ---------------------------------------------------------------------------

def backfill_symbol(symbol: str, start_str: str, end_str: str) -> Tuple[int, int]:
    """
    回算单个品种的历史打分。
    返回 (成功天数, 失败天数)
    """
    # 重置全局历史（跨品种不污染）
    global _CB_GOLD_CHG_HIST, _LME_CU_CHG_HIST
    _CB_GOLD_CHG_HIST = []
    _LME_CU_CHG_HIST = []

    # 解析日期
    start_dt = datetime.strptime(start_str, "%Y%m%d").date()
    end_dt   = datetime.strptime(end_str,   "%Y%m%d").date()

    # 生成日期序列
    dates = []
    d = start_dt
    while d <= end_dt:
        dates.append(d)
        d += timedelta(days=1)

    # 过滤：只保留工作日（跳过周末）
    dates = [d for d in dates if d.weekday() < 5]

    print(f"\n[{symbol}] 开始回算 {start_str} ~ {end_str}，共 {len(dates)} 个工作日 ...")

    # Step 1: 预加载缓存
    print("  [1/4] 预加载缓存...")
    _load_inventory_cache()
    _load_fx_cache()
    if symbol in ("CU", "AU", "AG"):
        _load_all_caches()

    # Step 2: 拉取 raw_data 序列
    print("  [2/4] 拉取每日原始数据 ...")
    raw_seq: List[Optional[dict]] = []
    for i, d in enumerate(dates):
        d_str = d.strftime("%Y%m%d")
        raw = fetch_daily_data(symbol, d_str)
        raw_seq.append(raw)
        if (i + 1) % 10 == 0:
            print(f"    进度 {i+1}/{len(dates)}")
        time.sleep(0.3)   # 防限速

    # Step 3: 对每个因子计算 raw_value 序列，然后归一化
    print("  [3/4] 计算因子 raw_value + 归一化 ...")
    factor_meta_list = FACTOR_META.get(symbol, FACTOR_META['RU'])

    norm_series_map: Dict[str, List[float]] = {}
    raw_series_map:  Dict[str, List[Optional[float]]] = {}

    for fm in factor_meta_list:
        code = fm["factor_code"]
        raw_seq_f = []
        prev_raw = None
        for raw in raw_seq:
            rv = compute_factor_raw(fm, raw or {}, prev_raw)
            raw_seq_f.append(rv)
            if raw is not None:
                prev_raw = raw
        raw_series_map[code] = raw_seq_f
        norm_series_map[code] = normalize_all(raw_seq_f)

    # Step 4: 逐日计算综合打分并写 CSV
    print("  [4/4] 写入 CSV 文件 ...")
    ok, fail = 0, 0
    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

    for i, (d, raw) in enumerate(zip(dates, raw_seq)):
        d_str = d.strftime("%Y%m%d")

        # 计算综合打分
        composite = 0.0
        factors_out = []
        for fm in factor_meta_list:
            code = fm["factor_code"]
            weight = fm["weight"]
            direction = fm["direction"]
            norm = norm_series_map[code][i] if i < len(norm_series_map[code]) else 0.0
            raw_v = raw_series_map[code][i] if i < len(raw_series_map[code]) else None

            # direction: positive → raw高对因子正；negative → raw高对因子负
            if direction == "negative":
                norm = -norm

            contrib = norm * weight
            composite += contrib

            factors_out.append({
                "factor_code": code,
                "factor_name": fm["factor_name"],
                "factor_direction": direction,
                "weight": weight,
                "normalized_score": norm,
                "raw_value": raw_v,
                "contribution": contrib,
                "ic_value": 0.0,   # backfill 不计算 IC
            })

        # 限制到 [-1, 1]
        composite = max(-1.0, min(1.0, composite))

        if composite > 0.15:
            direction = "LONG"
        elif composite < -0.15:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"

        try:
            p = write_csv(symbol, d_str, composite, direction, factors_out, updated_at)
            ok += 1
        except Exception as e:
            fail += 1
            print(f"    [FAIL] {d_str}: {e}")

        if (i + 1) % 10 == 0:
            print(f"    进度 {i+1}/{len(dates)}")

    print(f"\n  完成: 成功 {ok} 天，失败 {fail} 天")
    return ok, fail


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="宏观打分历史回算")
    parser.add_argument("--symbol", default="RU")
    parser.add_argument("--start",  default=DEFAULT_START)
    parser.add_argument("--end",    default=DEFAULT_END)
    args = parser.parse_args()

    if not HAS_AKSHARE:
        print("[ERROR] AKShare 未安装，无法拉取历史数据。")
        print("  安装命令: pip install akshare")
        exit(1)

    print(f"=" * 60)
    print(f"宏观打分历史回算脚本 v1.0")
    print(f"品种: {args.symbol}  范围: {args.start} ~ {args.end}")
    print(f"=" * 60)

    ok, fail = backfill_symbol(args.symbol.upper(), args.start, args.end)
    print(f"\n回算完成。成功 {ok} 天，失败 {fail} 天")
    print(f"CSV 输出目录: {CSV_BASE_DIR}")
