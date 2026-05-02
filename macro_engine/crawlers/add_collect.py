# -*- coding: utf-8 -*-
"""补充采集: CBOT大豆, 黄金白银比"""
import sys
import os
import datetime
import pandas as pd

sys.path.insert(0, 'D:/futures_v6/macro_engine/crawlers/common')
from db_utils import save_to_db, ensure_table
import akshare as ak

os.chdir('D:/futures_v6/macro_engine')
ensure_table()

def get_obs_date():
    today = datetime.date.today()
    dow = today.weekday()
    if dow == 0:
        obs_date = today - pd.Timedelta(days=2)
    elif dow == 6:
        obs_date = today - pd.Timedelta(days=2)
    else:
        obs_date = today
    return today, obs_date

pub_date, obs_date = get_obs_date()
print(f"pub={pub_date}, obs={obs_date}")

# Y - CBOT大豆
try:
    df = ak.futures_foreign_hist(symbol='ZSD')
    if df is not None and len(df) > 0:
        val = float(df.iloc[-1]['close'])
        print(f"Y_CBOT_SOYBEAN = {val}")
        # CBOT大豆价格范围: 800-4000 cents/bushel
        if 800 <= val <= 4000:
            ok = save_to_db("Y_CBOT_SOYBEAN", "Y", pub_date, obs_date, val,
                          source_confidence=1.0, source="AKShare-futures_foreign_hist(ZSD)")
            print(f"DB write: {ok}")
        else:
            print(f"Range check failed: {val}")
except Exception as e:
    print(f"Y_CBOT_SOYBEAN failed: {e}")

# AU/AG - 黄金白银比
try:
    au_df = ak.spot_golden_benchmark_sge()
    if au_df is not None and len(au_df) > 0:
        au_val = float(au_df.iloc[-1].iloc[1])
        print(f"AU spot = {au_val}")
        
        # 找白银价格
        ag_df = ak.macro_china_fx_gold()
        ag_val = None
        if ag_df is not None and len(ag_df) > 0:
            # 列: 月份, 黄金储备-金额, 黄金储备-同比, 白银储备-金额, 白银储备-同比
            # 实际上可能是月度数据
            for col in ag_df.columns:
                if '白银' in str(col):
                    ag_val = float(ag_df.iloc[-1][col])
                    break
        
        if ag_val and ag_val > 0:
            ratio = au_val / ag_val
            print(f"Au/Ag ratio = {ratio:.4f}")
            ok = save_to_db("AG_MACRO_GOLD_SILVER_RATIO", "AG", pub_date, obs_date, ratio,
                          source_confidence=1.0, source="AKShare-calculated(SGE/SGE)")
            print(f"DB write ratio: {ok}")
except Exception as e:
    print(f"Au/Ag ratio failed: {e}")

print("Done")
