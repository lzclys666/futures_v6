"""
DXY美元指数（美联储贸易加权广义美元指数）
因子: AU_DXY = DXY美元指数（美联储贸易加权广义美元指数）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- 数据源: L1a: 新浪财经 hf_DXY | L1b: 金十数据 | L1c: 东方财富 | L2: FRED DTWEXBGS | L4: DB回补
- 采集逻辑: 见脚本内多源漏斗
- bounds: 因因子而异

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os, re, requests
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

FACTOR_CODE = "AU_DXY"
SYMBOL = "AU"


def fetch_fred_dxy():
    """L2: FRED DTWEXBGS (美联储贸易加权广义美元指数 Broad Dollar Index)"""
    try:
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS&vintage_date={today}'
        r = requests.get(url, timeout=15)
        lines = r.text.strip().split('\n')
        for line in reversed(lines[1:]):
            parts = line.split(',')
            if len(parts) == 2 and parts[1].strip() != '.':
                val = float(parts[1].strip())
                obs_date = parts[0].strip()
                if 90 <= val <= 150:
                    print(f"[L2] DTWEXBGS={val} obs={obs_date} (FRED)")
                    return val, 0.9, f"FRED_DTWEXBGS"
    except Exception as e:
        print(f"[L2] FRED DTWEXBGS 失败: {e}")
    return None, None, None


def fetch_dxy():
    """尝试从多个源获取DXY"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # L1a: 新浪财经 DXY
    try:
        r = requests.get(
            'https://hq.sinajs.cn/list=hf_DXY',
            headers={'Referer': 'https://finance.sina.com.cn', 'User-Agent': headers['User-Agent']},
            timeout=10
        )
        r.encoding = 'gbk'
        m = re.search(r'"([^"]+)"', r.text)
        if m:
            parts = m.group(1).split(',')
            if len(parts) >= 1:
                val = float(parts[0])
                if 90 <= val <= 130:
                    print(f"[L1a] DXY={val} (Sina Finance)")
                    return val, 1.0, "sina_hq_hf_DXY"
    except Exception as e:
        print(f"[L1a] {e}")

    # L1b: 金十数据 flash API
    try:
        r = requests.get(
            'https://flash-api.jin10.com/get_flash_chart_data?max_time=9999999999',
            headers={'User-Agent': headers['User-Agent'], 'X-App-Id': 'jinseof'},
            timeout=10
        )
        data = r.json()
        for item in data.get('data', []):
            if 'DXY' in str(item) or 'dxy' in str(item):
                m = re.search(r'DXY[^0-9]*([0-9]+\.?[0-9]*)', str(item))
                if m:
                    val = float(m.group(1))
                    if 90 <= val <= 130:
                        print(f"[L1b] DXY={val} (Jin10)")
                        return val, 1.0, "jin10_flash_api"
    except Exception as e:
        print(f"[L1b] {e}")

    # L1c: 东方财富 DXY CFD
    try:
        r = requests.get(
            'https://push2.eastmoney.com/api/qt/stock/get?secid=106.CFDDXY&fields=f43,f57,f58,f169,f170,f47,f48&ut=fa5fd1943c7b386f172d6893dbfba10b',
            headers={'User-Agent': headers['User-Agent'], 'Referer': 'https://quote.eastmoney.com/'},
            timeout=10
        )
        data = r.json()
        val = data.get('data', {}).get('f43')
        if val and 90 <= val/100 <= 130:
            val = val / 100
            print(f"[L1c] DXY={val} (Eastmoney)")
            return val, 1.0, "eastmoney_cfd_dxy"
    except Exception as e:
        print(f"[L1c] {e}")

    # L2: FRED DTWEXBGS (Broad Dollar Index, trade-weighted)
    val2, conf2, src2 = fetch_fred_dxy()
    if val2 is not None:
        return val2, conf2, src2

    # L4: 历史回补
    latest = get_latest_value(FACTOR_CODE, SYMBOL)
    if latest is not None:
        print(f"[L4] DXY={latest} (L4 fallback from DB)")
        return latest, 0.5, "L4_historical_fallback"
    else:
        print("[WARN] AU_DXY无任何数据源且DB无历史值，请手动录入")
        return None, None, None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()

    val, conf, src = fetch_dxy()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=conf, source=src)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        print(f"[WARN] {FACTOR_CODE} 无数据")


if __name__ == "__main__":
    main()
