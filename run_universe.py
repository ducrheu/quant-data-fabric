"""Manual run: build the point-in-time universe snapshot.

抽样源用 2025-01-02 的全市场返回，而不是今天的股票列表 ——
那天在场的票里包含后来退市的，从"今天"抽会把它们系统性剔除（幸存者偏差）。
"""

import tushare as ts

from src.config import get_tushare_token
from src.universe import UNIVERSE_PATH, save_universe, select_universe

AS_OF_TRADE_DATE = "20250102"
SIZE = 300
SEED = 20250102

def main():
    pro = ts.pro_api(get_tushare_token())

    frame = pro.daily(trade_date=AS_OF_TRADE_DATE)
    codes = [
        code for code in frame["ts_code"].tolist()
        if code.endswith(".SH") or code.endswith
    ]

    selected = select_universe(codes, SIZE, SEED)
    save_universe(
        symbols=selected,
        as_of=AS_OF_TRADE_DATE,
        seed=SEED,
        candidates=len(codes),
        path=UNIVERSE_PATH,
    )

    print(f"as_of = {AS_OF_TRADE_DATE} candidates = {len(codes)} picked = {len(selected)}")
    print(f"head: {selected[:5]}")
    print(f"saved: {UNIVERSE_PATH}")

if __name__ == "__main__":
    main()