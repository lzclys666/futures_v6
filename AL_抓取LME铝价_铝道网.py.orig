#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_抓取LME铝价_铝道网.py
因子: AL_LME_PRICE = LME铝现货价（美元/吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- 数据源: 铝道网(hq.alu.cn)，L2免费聚合，解析页面中的LME铝现货价格
- 采集逻辑: 正则提取标题或表格数据
- bounds: [1500, 5000]美元/吨（2020年来LME铝价区间）

订阅优先级: ★★（铝道网免费数据）
替代付费源: LME官网（免费但需解析）
"""
import sys, os, re, datetime
import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates

FACTOR_CODE = "AL_LME_PRICE"
SYMBOL = "AL"
DATA_SOURCE = "铝道网(hq.alu.cn)"
URL = "https://hq.alu.cn/lmeld.html"
BOUNDS = (1500, 5000)


def fetch_lme_price():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        resp = requests.get(URL, headers=headers, timeout=15)
        resp.encoding = "gb2312"
        if resp.status_code != 200:
            print(f"[ERR] HTTP {resp.status_code}")
            return None

        html = resp.text

        # 策略1: 标题解析
        # 格式: 2026年04月16日LME伦敦金属交易所现货行情价3618
        m = re.search(r"(\d{4})年(\d{2})月(\d{2})日LME.*?现货行情价([\d.]+)", html)
        if m:
            year, month, day, price = m.groups()
            obs_date = f"{year}-{month}-{day}"
            price_val = float(price)
            if BOUNDS[0] <= price_val <= BOUNDS[1]:
                print(f"[L2] 成功({obs_date}): ${price_val}/ton")
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
                        # 转换日期: 04-16 → 2026-04-16
                        parts = date_cell.split("-")
                        obs_date = f"{datetime.date.today().year}-{parts[0]}-{parts[1]}"
                        print(f"[L2] 表格解析({obs_date}): ${price_val}/ton")
                        return price_val, obs_date
                except ValueError:
                    continue

        print("[WARN] 页面中未解析出LME铝价数据")
        return None, None

    except requests.exceptions.RequestException as e:
        print(f"[ERR] 网络异常: {e}")
        return None, None
    except Exception as e:
        print(f"[ERR] 解析异常: {e}")
        return None, None


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    price, data_date = fetch_lme_price()
    if price is not None:
        # 数据日期应与obs_date一致或接近
        if data_date:
            # 使用数据实际日期作为obs_date（更准确）
            obs_date = data_date
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, price,
                   source=DATA_SOURCE, source_confidence=0.9)
        print(f"[OK] {FACTOR_CODE}={price} (obs={obs_date})")
    else:
        print(f"[ERR] {FACTOR_CODE} 抓取失败")
