#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FU_国内现货价.py
因子: FU_SPOT_DOMESTIC = 国内燃料油现货价格（元/吨）

公式: Ship&Bunker新加坡IFO380(HSFO) × USD/CNY汇率

当前状态: [OK]正常
- L1: Ship&Bunker新加坡IFO380(HSFO) + Sina USD/CNY汇率
- L2: None
- L3: None
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

数据源说明：
  energy_oil_hist() 返回的是汽柴油价格(8705-9770元/吨)，不是燃料油现货价(~4500-5300元/吨)。
  改用 Ship&Bunker 新加坡 IFO380 报价 + Sina汇率换算。

订阅优先级: 无（免费源）
替代付费源: 隆众资讯（舟山燃料油保税价，年费）
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, _get_latest_record
from common.web_utils import fetch_url
import requests
from datetime import datetime

FACTOR_CODE = "FU_SPOT_DOMESTIC"
SYMBOL = "FU"
BOUNDS = (2000, 12000)


def fetch():
    """L1: Ship&Bunker新加坡IFO380(HSFO) × Sina USD/CNY汇率"""
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

        # Step 3: 换算为CNY
        spot_cny = hsfo_usd * usdcny
        date_str = datetime.now().strftime("%Y-%m-%d")
        print(f"[L1] 燃料油现货(CNY): {spot_cny:.1f} 元/吨")

        return spot_cny, date_str

    except Exception as e:
        print(f"[L1] Ship&Bunker方案失败: {e}")
        return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val, obs_dt = fetch()
    if val is None:
        record = _get_latest_record(FACTOR_CODE, SYMBOL)
        if record:
            raw_value, orig_obs_date, orig_source, orig_conf = record
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                        source_confidence=0.5, source=f"L4回补({orig_source})")
            print(f"[L4] {FACTOR_CODE}={raw_value} 回补成功")
            return
        print(f"[L5] {FACTOR_CODE}: 所有数据源失效，不写占位符")
        return
    if obs_dt:
        obs_date = obs_dt
    if not (BOUNDS[0] <= val <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
        return
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                source_confidence=0.85, source='ShipBunker_IFO380_x_CNY')
    print(f"[OK] {FACTOR_CODE}={val:.1f}")


if __name__ == "__main__":
    main()
