#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次2_月报爬虫
因子: 待定义 = 批次2_月报爬虫

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os, re
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from common.web_utils import fetch_url, fetch_json
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
from datetime import date

FACTOR_MAP = {
    'P_PROD_MPOB': 'production',
    'P_EXP_MPOB': 'exports',
    'P_STOCK_MPOB': 'ending_stocks',
}
EXPECTED = {
    'P_PROD_MPOB': (800000, 2000000),  # 吨/月
    'P_EXP_MPOB': (500000, 2000000),
    'P_STOCK_MPOB': (500000, 5000000),
}

MPOB_URL = 'https://www.mpob.gov.my/index.php/economic/commodity/primary/103-palm-oil/2807-monthly-production'

def fetch_mpob():
    """从MPOB官网抓取月度棕榈油数据"""
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        html, err = fetch_url(MPOB_URL, headers=headers, timeout=15)
        if err:
            raise ValueError(err)
    except Exception as e:
        raise ValueError('MPOB fetch FAIL: ' + str(e)[:60])

    # 解析HTML中的表格数据
    # MPOB月报格式: 产量/出口/库存表格
    data = {}
    # 尝试解析表格
    try:
        import pandas as pd
        tables = pd.read_html(html)
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            # 找产量行
            for _, row in t.iterrows():
                row_str = ' '.join([str(v).lower() for v in row.values])
                if 'production' in row_str or '\u4ea7\u91cf' in row_str or 'mt' in row_str:
                    # 提取数值
                    for v in row.values:
                        try:
                            val = float(str(v).replace(',', '').replace(' ', ''))
                            if 500000 < val < 5000000:
                                data['production'] = val
                                break
                        except (ValueError, IndexError):
                            pass
                if 'export' in row_str or '\u51fa\u53e3' in row_str:
                    for v in row.values:
                        try:
                            val = float(str(v).replace(',', '').replace(' ', ''))
                            if 300000 < val < 5000000:
                                data['exports'] = val
                                break
                        except (ValueError, IndexError):
                            pass
                if 'stock' in row_str or '\u5e93\u5b58' in row_str or 'ending' in row_str:
                    for v in row.values:
                        try:
                            val = float(str(v).replace(',', '').replace(' ', ''))
                            if 500000 < val < 8000000:
                                data['ending_stocks'] = val
                                break
                        except (ValueError, IndexError):
                            pass
    except Exception as e:
        raise ValueError('Table parse FAIL: ' + str(e)[:60])

    if not data:
        raise ValueError('No MPOB data found in page')

    # 解析月份 - 找最新月份
    month_match = re.search(r'(January|February|...|December)\s+(\d{4})', html, re.I)
    if not month_match:
        month_map = {'january':'01','february':'02','march':'03','april':'04',
                      'may':'05','june':'06','july':'07','august':'08',
                      'september':'09','october':'10','november':'11','december':'12'}
        month_str = month_match.group(1).lower() if month_match else '01'
        year_str = month_match.group(2) if month_match else str(date.today().year)
        month_num = month_map.get(month_str, '01')
        obs_date = date(int(year_str), int(month_num), 1)
    else:
        obs_date = date.today().replace(day=1)

    return data, obs_date

def save_factor(fc, val, obs):
    em = EXPECTED.get(fc, (0, 999999999))
    if not (em[0] <= val <= em[1]):
        print('[WARN] ' + fc + '=%.0f out of [%d,%d]' % (val, em[0], em[1]))
        return
    save_to_db(fc, 'P', date.today(), obs, val, source_confidence=0.8)
    print('[OK] ' + fc + '=%.0f obs=%s' % (val, obs))

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f'=== P批次2 === pub={pub_date} obs={obs_date}')

    try:
        data, obs_date = fetch_mpob()
    except Exception as e:
        print('[L1 FAIL] P_batch2: ' + str(e)[:80])
        for fc in FACTOR_MAP:
            save_l4_fallback(fc, 'P', pub_date, obs_date)
        return

    for fc, key in FACTOR_MAP.items():
        if key in data:
            save_factor(fc, data[key], obs_date)
        else:
            save_l4_fallback(fc, 'P', pub_date, obs_date)

if __name__ == '__main__':
    main()
