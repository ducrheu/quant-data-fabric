"""Manual run: build reference-data snapshots (universe + trading calendar).

这两样都是"抓一次、长期不变"的参考数据：
- 股票池：抽样不可重复，且要带 as_of 出处（防幸存者偏差）
- 交易日历：用上证指数日线一次取全 —— trade_cal 限频实测 1次/分钟~1次/小时，不可用
"""

from collections import Counter
from datetime import datetime, timedelta

import tushare as ts

from src.config import get_tushare_token
from src.universe import UNIVERSE_PATH, save_universe, select_universe
from src.trading_calendar import TRADING_CALENDAR_PATH, save_trading_days

AS_OF_TRADE_DATE = "20250102"
SIZE = 300
SEED = 20250102
CALENDAR_START = "20250102"
CALENDAR_END = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
CALENDAR_INDEX = "000001.SH"

def fetch_calendar(pro):
    """上证指数一次调用即完整日历：指数只在交易日存在，且不会停牌。

    （备选方案：拉多只大盘股日线取并集 —— 只有 index_daily 不可用时才需要。）
    """
    frame = pro.index_daily(
        ts_code = CALENDAR_INDEX,
        start_date = CALENDAR_START,
        end_date = CALENDAR_END,
    )
    days = sorted(frame["trade_date"].tolist())
    print(f"{CALENDAR_INDEX} -> {len(days)} days ({days[0]} ~ {days[-1]}")
    return days

def main():
    pro = ts.pro_api(get_tushare_token())

    frame = pro.daily(trade_date=AS_OF_TRADE_DATE)
    codes = [
        code for code in frame["ts_code"].tolist()
        if code.endswith(".SH") or code.endswith(".SZ")
    ]
    print("by suffix:", dict(Counter(code.split(".")[-1] for code in codes)))

    selected = select_universe(codes, SIZE, SEED)
    save_universe(
        symbols=selected,
        as_of=AS_OF_TRADE_DATE,
        seed=SEED,
        candidates=len(codes),
        path=UNIVERSE_PATH,
    )

    print(f"as_of = {AS_OF_TRADE_DATE} candidates = {len(codes)} picked = {len(selected)}")

    days = fetch_calendar(pro)
    save_trading_days(
        days, CALENDAR_START, CALENDAR_END, "tushare.index_daily",
    )
    print(f"calendar: {len(days)} days ({days[0]} ~ {days[-1]}) -> {TRADING_CALENDAR_PATH}")

if __name__ == "__main__":
    main()