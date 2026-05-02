"""
SPDR黄金ETF持仓量（吨）
因子: AU_SPD_GLD = SPDR黄金ETF持仓量（吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- 数据源: L1a: 我的钢铁网 | L1b: 东方财富API | L1c: 新浪贵金属 | L4: DB回补
- 采集逻辑: 见脚本内多源漏斗
- bounds: 因因子而异

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os, re, requests
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

FACTOR_CODE = "AU_SPD_GLD"
SYMBOL = "AU"


def fetch_spdr():
    """尝试从多个源获取SPDR黄金持仓（吨）"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # L1a: 我的钢铁网 SPDR黄金持仓
    try:
        r = requests.get(
            'https://news.mysteel.com/a/26041709/',
            headers={'User-Agent': headers['User-Agent']},
            timeout=10
        )
        r.encoding = 'utf-8'
        text = r.text
        # Pattern: SPDR Gold Trust持仓量为XXXX.XX吨
        m = re.search(r'SPD[Rr].*?持仓量[为]?(\d+\.?\d*)\s*吨', text)
        if not m:
            m = re.search(r'持仓[为]?(\d+\.?\d{2})\s*吨', text[:3000])
        if m:
            val = float(m.group(1))
            if 500 <= val <= 2000:
                print(f"[L1a] SPDR GLD={val}吨 (Mysteel)")
                return val, 1.0, "mysteel_spdr_gld"
    except Exception as e:
        print(f"[L1a] {e}")

    # L1b: 东方财富 SPDR持仓快讯搜索（需要动态内容）
    # 尝试东方财富数据API
    try:
        r = requests.get(
            'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_GOLD_ETF_HOLD&columns=ALL&pageNumber=1&pageSize=5',
            headers={'User-Agent': headers['User-Agent'], 'Referer': 'https://data.eastmoney.com/'},
            timeout=10
        )
        data = r.json()
        for item in data.get('result', {}).get('data', []):
            if 'SPDR' in str(item) or 'GLD' in str(item):
                hold = item.get('F8') or item.get('hold')  # 持仓量
                if hold and 500 <= float(hold) <= 2000:
                    val = float(hold)
                    print(f"[L1b] SPDR GLD={val}吨 (Eastmoney API)")
                    return val, 1.0, "eastmoney_gold_etf"
    except Exception as e:
        print(f"[L1b] {e}")

    # L1c: 尝试爬取新浪贵金属
    try:
        r = requests.get(
            'https://hq.sinajs.cn/list=hf_GLD',
            headers={'Referer': 'https://finance.sina.com.cn', 'User-Agent': headers['User-Agent']},
            timeout=10
        )
        r.encoding = 'gbk'
        m = re.search(r'"([^"]+)"', r.text)
        if m:
            parts = m.group(1).split(',')
            # GLD data format: last price, change, etc.
            for p in parts:
                try:
                    val = float(p)
                    if 500 <= val <= 2000:
                        print(f"[L1c] SPDR GLD={val} (Sina GLD)")
                        return val, 1.0, "sina_hq_hf_GLD"
                except:
                    pass
    except Exception as e:
        print(f"[L1c] {e}")

    # L4: 历史回补
    latest = get_latest_value(FACTOR_CODE, SYMBOL)
    if latest is not None:
        print(f"[L4] SPDR GLD={latest}吨 (L4 fallback from DB)")
        return latest, 0.5, "L4_historical_fallback"
    else:
        print("[WARN] AU_SPD_GLD无任何数据源且DB无历史值，请手动录入")
        return None, None, None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates()

    val, conf, src = fetch_spdr()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=conf, source=src)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        print(f"[WARN] {FACTOR_CODE} 无数据")


if __name__ == "__main__":
    main()
