"""Manual research script: parameter sensitivity for the momentum factor.

对每个窗口 H ∈ {10, 20, 40}：
- 用 H 日动量作为因子
- 用 H 日前瞻收益作为评价目标
- 用 H 个交易日作为回测调仓周期（非重叠、次日开盘成交）

**这是稳健性检验，不是调参**：目的是看结论是否只在某一个窗口下成立，
而不是挑一个最好看的窗口。
"""

import duckdb
import pandas as pd

from src.config import PRICE_DB_PATH
from src.factors.backtest import backtest, cumulative_net, sharpe
from src.factors.evaluate import (
    long_short_spread,
    newey_west_t_stat,
    quantile_returns,
    rank_ic,
)

HORIZONS = (10, 20, 40)
QUANTILES = 5
TRADING_DAYS_PER_YEAR = 252

def load_panels():
    """读收盘价与开盘价，各透视成 (交易日 × 股票) 的面板。"""
    con = duckdb.connect(PRICE_DB_PATH, read_only=True)
    price = con.execute(
        "SELECT symbol, trade_time, close, open, FROM price_daily ORDER BY symbol, trade_time"
    ).fetch_df()
    con.close()

    close_panel = price.pivot(index="trade_time", columns="symbol", values="close")
    open_panel = price.pivot(index="trade_time", columns="symbol", values="open")
    return close_panel, open_panel

def long_frame(factor_panel, forward_panel):
    """两个宽面板摊成长表，交给 evaluate 里的纯函数用。"""
    frame = pd.DataFrame({
        "value": factor_panel.stack(),
        "forward_return": forward_panel.stack(),
    })
    frame.index.names = ["trade_time", "symbol"]
    return frame.reset_index().dropna()

def main():
    close_panel, open_panel = load_panels()

    print(f"{'H':>3} {'IC':>8} {'ICt(NW)':>8} {'spread':>8} {'sprt(NW)':>9} "
          f"{'n':>4} {'total':>9} {'sharpe':>7} {'turn':>7}")

    for horizon in HORIZONS:
        factor_full = close_panel / close_panel.shift(horizon) - 1.0
        forward_full = close_panel.shift(-horizon) / close_panel - 1.0

        # 因子的前 horizon 行是全 NaN（还没攒够窗口），必须先切掉——
        # 否则回测的第一个调仓日会拿到一个空序列
        index = factor_full.dropna(how="all").index
        factor_panel = factor_full.loc[index]
        forward_panel = forward_full.loc[index]
        price_panel = open_panel.loc[index]

        data = long_frame(factor_panel, forward_panel)

        ic = rank_ic(data)
        quantiles = quantile_returns(data, QUANTILES)
        spread = long_short_spread(quantiles)

        result = backtest(factor_panel, price_panel, step=horizon, n_quantiles=QUANTILES)
        net = cumulative_net(result["spread"])
        total = float(net.iloc[-1] - 1.0)

        print(
            f"{horizon:>3} {ic.mean():>+8.4f} {newey_west_t_stat(ic, horizon - 1):>+8.2f} "
            f"{spread.mean():>+8.4f} {newey_west_t_stat(spread, horizon - 1):>+9.2f} "
            f"{len(result):>4} {total:>+9.2%} "
            f"{sharpe(result['spread'], TRADING_DAYS_PER_YEAR / horizon):>+7.2f} "
            f"{result['turnover'].mean():>7.2%}"
        )

if __name__ == "__main__":
    main()