#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_抓取现货和基差.py
因子: FU_BASIS = 燃料油期现基差（期货收盘价 - 舟山燃料油保税价，元/吨）

公式: 基差 = FU期货结算价 - 新加坡IFO380现货价(换算CNY)

当前状态: [OK]正常
- L1: Ship&Bunker新加坡IFO380(HSFO) + Sina USD/CNY汇率 + Sina FU期货结算价
- L2: AKShare futures_spot_price (100ppi.com) — 原方法，备用
- L3: 备用
- L4: DB回补
- L5: NULL占位

数据源说明：
  100ppi.com (生意社) 已被封禁(454)，AKShare futures_spot_price 无法获取数据。
  energy_oil_hist() 返回的是汽柴油价格(8705-9770元/吨)，不是燃料油现货价。
  改用 Ship&Bunker 新加坡 IFO380 报价 + 汇率换算。

订阅优先级: 无（免费源）
替代付费源: 隆众资讯（舟山燃料油保税价，年费）
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
from common.web_utils import fetch_url
import requests

FACTOR_CODE = "FU_BASIS"
SYMBOL = "FU"
BOUNDS = (-5000, 500)  # 期现基差，燃料油现货(保税380CST)经常高于期货


def fetch_basis_shipandbunker():
    """L1: Ship&Bunker新加坡IFO380(HSFO) + Sina汇率 + Sina FU期货 → 计算基差

    Ship&Bunker提供新加坡船舶燃油现货价(USD/mt)，Sina提供USD/CNY汇率和FU期货结算价。
    基差 = FU期货结算价(CNY) - IFO380现货价(USD) × USD/CNY汇率
    """
    try:
        # Step 1: 获取新加坡 IFO380 现货价 (USD/mt)
        url = "https://shipandbunker.com/prices"
        text, err = fetch_url(url, encoding='utf-8', timeout=20)
        if err:
            print(f"[L1] Ship&Bunker获取失败: {err}")
            return None, None

        hsfo_match = re.search(
            r'id="row-sg-sin-IFO380"[^>]*>.*?headers="price-IFO380">([\d.]+)',
            text, re.DOTALL
        )
        if not hsfo_match:
            # 尝试备用页面
            sg_url = "https://shipandbunker.com/prices/apac/sea/sg-sin-singapore"
            text2, err2 = fetch_url(sg_url, encoding='utf-8', timeout=20)
            if err2:
                print(f"[L1] Ship&Bunker备用页失败: {err2}")
                return None, None
            hsfo_match = re.search(
                r'id="row-sg-sin-IFO380"[^>]*>.*?headers="price-IFO380">([\d.]+)',
                text2, re.DOTALL
            )
        if not hsfo_match:
            print("[L1] Ship&Bunker: 未找到新加坡IFO380数据")
            return None, None

        hsfo_usd = float(hsfo_match.group(1))
        print(f"[L1] 新加坡IFO380: ${hsfo_usd}/mt")

        # Step 2: 获取USD/CNY汇率 (Sina)
        r = requests.get("https://hq.sinajs.cn/list=fx_susdcny",
                        headers={"Referer": "https://finance.sina.com.cn"}, timeout=10)
        r.encoding = 'gbk'
        fx_parts = r.text.split('"')[1].split(',')
        if len(fx_parts) < 2:
            print("[L1] Sina USD/CNY获取失败")
            return None, None
        usdcny = float(fx_parts[1])
        print(f"[L1] USD/CNY: {usdcny}")

        # Step 3: 获取FU期货结算价 (Sina)
        r2 = requests.get("https://hq.sinajs.cn/list=nf_FU0",
                         headers={"Referer": "https://finance.sina.com.cn"}, timeout=10)
        r2.encoding = 'gbk'
        fu_parts = r2.text.split('"')[1].split(',')
        if len(fu_parts) < 10:
            print("[L1] Sina FU期货获取失败")
            return None, None
        # Sina格式: 名称,昨收,开盘,最高,最低,买1价,结算价,收盘价,...,日期(index17)
        fut_settle = float(fu_parts[6])  # 结算价
        fut_date = fu_parts[17].strip() if len(fu_parts) > 17 else datetime.now().strftime("%Y-%m-%d")
        print(f"[L1] FU期货结算价: {fut_settle} (date: {fut_date})")

        # Step 4: 计算基差 = 期货结算价 - 现货价(CNY)
        spot_cny = hsfo_usd * usdcny
        basis = fut_settle - spot_cny
        date_str = fut_date if fut_date else datetime.now().strftime("%Y-%m-%d")
        print(f"[L1] 现货(CNY): {spot_cny:.1f} | 期货: {fut_settle} | 基差: {basis:.1f}")

        return basis, date_str

    except Exception as e:
        print(f"[L1] Ship&Bunker方案失败: {e}")
        return None, None


def fetch_basis_akshare():
    """L2: AKShare futures_spot_price 直接获取基差 (100ppi.com, 可能被封)"""
    try:
        import akshare as ak
        from datetime import datetime, timedelta
        for days_back in range(7):
            check_date = datetime.now() - timedelta(days=days_back)
            if check_date.weekday() >= 5:
                continue
            date_str = check_date.strftime("%Y%m%d")
            try:
                df = ak.futures_spot_price(date=date_str, vars_list=["FU"])
                if df is not None and len(df) > 0:
                    row = df.iloc[0]
                    basis = float(row["dom_basis"])
                    spot = float(row["spot_price"])
                    fut = float(row["dominant_contract_price"])
                    obs = str(row["date"])[:10]
                    print(f"[L2] AKShare基差({obs}): 现货={spot} 期货={fut} 基差={basis}")
                    return basis, obs
                else:
                    print(f"[L2] {date_str}: 无数据")
            except Exception as e:
                err_str = str(e)
                if '非交易日' not in err_str and '连接失败' not in err_str:
                    print(f"[L2] {date_str}: {err_str[:80]}")
                continue
    except Exception as e:
        print(f"[L2] AKShare失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")

    val, source = None, None

    # L1: Ship&Bunker + Sina
    val, source = fetch_basis_shipandbunker()
    if val is not None:
        if not (BOUNDS[0] <= val <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=0.85, source=f"L1-ShipBunker+Sina:{source}")
        print(f"[OK] {FACTOR_CODE}={val:.1f}")
        return

    # L2: AKShare直接基差 (100ppi.com)
    val, source = fetch_basis_akshare()
    if val is not None:
        if not (BOUNDS[0] <= val <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                    source_confidence=1.0, source=f"L2-AKShare基差:{source}")
        print(f"[OK] {FACTOR_CODE}={val}")
        return

    # L4: DB fallback
    record = _get_latest_record(FACTOR_CODE, SYMBOL)
    if record:
        raw_value, orig_obs_date, orig_source, orig_conf = record
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                    source_confidence=0.5, source=f"L4回补({orig_source})")
        print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
        return

    print(f"[L5] {FACTOR_CODE}: 所有数据源失效，不写占位符")


if __name__ == "__main__":
    from datetime import datetime
    main()
