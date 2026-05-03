# scripts/scheduler.py
import schedule
import time
import os
from datetime import date
from core.data.collector import FuturesDataCollector

TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "PLEASE_SET_ENV")
# 多品种支持：可配置化扩展
SYMBOLS = ["RU", "AU"]  # 支持 RU 橡胶 + AU 黄金双品种

def daily_update():
    print(f"[{date.today()}] 开始更新数据...")
    collector = FuturesDataCollector(tushare_token=TUSHARE_TOKEN)
    for symbol in SYMBOLS:
        collector.collect_and_store(symbol, date.today())
    print(f"[{date.today()}] 数据更新完成。")

# 每天 17:00 执行（收盘后）
schedule.every().day.at("17:00").do(daily_update)

if __name__ == "__main__":
    print("定时任务已启动，每天 17:00 自动更新数据...")
    while True:
        schedule.run_pending()
        time.sleep(60)