#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_抓取LME铝价_铝道网.py
因子: AL_LME_PRICE = LME铝现货价（美元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: 铝道网(hq.alu.cn)，source_confidence=0.9（免费源，无L2备选）
- L2: 无备选源（铝道网为唯一免费LME铝价来源）
- bounds: [1500, 5000]美元/吨（2020年来LME铝价区间）
- 注: L3回补已添加（2026-05-05）

订阅优先级: ★★（铝道网免费数据）
替代付费源: LME官网（免费但需解析）
注: 铝道网页面解析失败时走L3回补（2026-05-05）
"""
import sys, os, re, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

from common.web_utils import fetch_url

FACTOR_CODE = "AL_LME_PRICE"
SYMBOL = "AL"
DATA_SOURCE = "铝道网(hq.alu.cn)"
URL = "https://hq.alu.cn/lmeld.html"
BOUNDS = (1500, 5000)


def fetch_lme_price():
    try:
        headers = {
            "Accept": "text/html",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        html, err = fetch_url(URL, headers=headers, timeout=15)
        if err:
            print(f"[ERR] 网络异常: {err}")
            return None, None

        # 策略1: 标题解析
        # 格式: 2026年04月16日LME伦敦金属交易所现货行情价3618
        m = re.search(r"(\d{4})年(\d{2})月(\d{2})日LME.*?现货行情价([\d.]+)", html)
        if m:
            year, month, day, price = m.groups()
            obs_date = f"{year}-{month}-{day}"
            price_val = float(price)
            if BOUNDS[0] <= price_val <= BOUNDS[1]:
                print(f"[L1] 成功({obs_date}): ${price_val}/ton")
                return price_val, obs_date

        # 策略2: 表格解析
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            if len(cells) >= 6 and "LME" in cells[1] and "铝" in cells[1]:
                date_cell = cells[0]
                close_price = cells[2]
                try:
                    price_val = float(close_price)
                    if BOUNDS[0] <= price_val <= BOUNDS[1]:
                        parts = date_cell.split("-")
                        obs_date = f"{datetime.date.today().year}-{parts[0]}-{parts[1]}"
                        print(f"[L1] 表格解析({obs_date}): ${price_val}/ton")
                        return price_val, obs_date
                except ValueError:
                    continue

        print("[WARN] 页面中未解析出LME铝价数据")
        return None, None

    except Exception as e:
        print(f"[ERR] 网络异常: {e}")
        return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return

    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    price, data_date = fetch_lme_price()
    if price is not None:
        if data_date:
            obs_date = data_date
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, price,
                   source=DATA_SOURCE, source_confidence=0.9)
        print(f"[OK] {FACTOR_CODE}={price} (obs={obs_date})")
        return

    # L3: 兜底保障
    if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                         extra_msg="(LME铝价)"):
        pass
    else:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                   source_confidence=0.0, source="all_sources_failed")
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")


if __name__ == "__main__":
    main()
