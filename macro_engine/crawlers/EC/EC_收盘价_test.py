# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from config.paths import CRAWLERS
"""
娆х嚎鏈熻揣鏀剁洏浠?
鍥犲瓙: 寰呭畾涔?= 娆х嚎鏈熻揣鏀剁洏浠?

鍏紡: 鏁版嵁閲囬泦锛堟棤鐙珛璁＄畻鍏紡锛?

褰撳墠鐘舵€? 鈿狅笍寰呬慨澶?
- 鑴氭湰宸叉湁鏁版嵁鑾峰彇閫昏緫锛孒eader寰呭畬鍠?
- 灏濊瘯杩囩殑鏁版嵁婧愬強缁撴灉锛氶渶琛ュ厖
- 瑙ｅ喅鏂规锛氶渶琛ュ厖

璁㈤槄浼樺厛绾? 鈽呪槄锛堜粯璐规簮鎵嶉渶瑕佹爣娉級
鏇夸唬浠樿垂婧? 鍏蜂綋骞冲彴鍚嶇О
"""
sys.path.insert(0, str(CRAWLERS / 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
import pandas as pd

FCODE = "EC_FUT_CLOSE"
SYM = "EC"
EMIN = 500
EMAX = 10000

def fetch():
    df = ak.futures_main_sina(symbol="EC0")
    if df.empty:
        raise ValueError("EC0 no data")
    # 鏁版嵁宸叉寜鏃ユ湡鍗囧簭鎺掑垪锛屾渶鍚庝竴琛?鏈€鏂?
    # 鍒? [0]=鏃ユ湡, [1]=寮€鐩? [2]=楂? [3]=浣? [4]=鏀剁洏, [5]=鎴愪氦閲? [6]=鎸佷粨, [7]=缁撶畻
    latest = df.iloc[-1]
    obs_date = pd.to_datetime(latest.iloc[0]).date()
    raw_value = float(latest.iloc[4])  # 鏀剁洏浠?
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1] " + FCODE + ": " + str(e))
        latest = get_latest_value(FCODE, SYM)
        if latest is not None:
            print("[L4] " + FCODE + "=" + str(latest))
        else:
            print("[SKIP] " + FCODE)
        return
    if not (EMIN <= raw_value <= EMAX):
        print("[WARN] " + FCODE + "=" + str(raw_value) + " [" + str(EMIN) + "," + str(EMAX) + "]")
        return
    save_to_db(FCODE, SYM, datetime.date.today(), obs_date, raw_value, source_confidence=1.0)
    print("[OK] " + FCODE + "=" + str(raw_value) + " obs=" + str(obs_date))

if __name__ == "__main__":
    main()
