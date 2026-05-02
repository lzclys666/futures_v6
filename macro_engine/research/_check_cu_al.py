"""检查 CU/AL ratio 和 AU/AG ratio 数据"""
import pandas as pd
import os

paths = [
    r'D:\futures_v6\macro_engine\data\crawlers\shared\daily\CU_AL_ratio.csv',
    r'D:\futures_v6\macro_engine\data\crawlers\_shared\daily\AU_AG_ratio_corrected.csv',
]

for p in paths:
    try:
        df = pd.read_csv(p)
        fname = os.path.basename(p)
        print(fname + ':')
        print('  Rows: ' + str(len(df)) + ', Columns: ' + str(list(df.columns)))
        print('  Index: ' + str(df.index[0]) + ' ~ ' + str(df.index[-1]))
        last = df.iloc[-1].to_dict()
        print('  Latest: ' + str(last))
    except FileNotFoundError:
        print('NOT FOUND: ' + p)
