"""Manual research script: neutralize mom_20d against liquidity (amount).

回答一个问题：**20 日动量的反转，是不是低流动性（小票）股票的投影？**

暴露用 price_daily.amount（当日成交额）的对数——它是市值的一个代理。
真正的市值中性化要等 daily_basic 数据拉全（该接口限频 1 次/小时）。
"""

import duckdb
import numpy as np
import pandas as pd

from src.config import PRICE_DB_PATH
from src.factors.backtest import backtest, cumulative_net, sharpe
from src.factors.evaluate import (
    long_short_spread,
    newey_west_t_stat,
    quantile_returns,
    rank_ic,
)

from src.factors.momentum import forward_return_frame, momentum_frame
from src.factors.neutralize import neutralize_panel

HORIZON = 20
QUANTILES = 5
TRADING_DAYS_PER_YEAR = 252

def load_panels():
    con = duckdb.connect(PRICE_DB_PATH, read_only=True)
    prices = con.execute(
        "SELECT symbol, trade_time, close, open, amount FROM price_daily ORDER BY symbol, trade_time"
    ).fetch_df()
    con.close()

    close_panel = prices.pivot(index="trade_time", columns="symbol", values="close")
    open_panel = prices.pivot(index="trade_time", columns="symbol", values="open")
    amount_panel = prices.pivot(index="trade_time", columns="symbol", values="amount")
    return prices, close_panel, open_panel, amount_panel

def long_frame(factor_panel, forward_panel):
    frame = pd.DataFrame({
        "value": factor_panel.stack(),
        "forward_return": forward_panel.stack()
    })
    frame.index.names = ["trade_time", "symbol"]
    return frame.reset_index().dropna()

def report(tag, factor_panel, forward_panel, price_panel):
    data = long_frame(factor_panel, forward_panel)
    ic = rank_ic(data)
    quantiles = quantile_returns(data, QUANTILES)
    spread = long_short_spread(quantiles)

    result = backtest(factor_panel, price_panel, step=HORIZON, n_quantiles=QUANTILES)
    net = cumulative_net(result["spread"])

    print(
        f"{tag:<12} {ic.mean():>+8.4f} {newey_west_t_stat(ic, HORIZON - 1):>+7.2f}  "
        f"{spread.mean():>+8.4f} {newey_west_t_stat(spread, HORIZON - 1):>+7.2f}  "
        f"{float(net.iloc[-1] - 1.0):>+8.2%}  "
        f"{sharpe(result['spread'], TRADING_DAYS_PER_YEAR / HORIZON):>+6.2f}"
    )

def main():
    prices, close_panel, open_panel, amount_panel = load_panels()

    factor_panel = momentum_frame(prices, HORIZON).pivot(
        index="trade_time", columns="symbol", values="value"
    )
    forward_panel_full = forward_return_frame(prices, HORIZON).pivot(
        index="trade_time", columns="symbol", values="value"
    )

    index = factor_panel.index.intersection(open_panel.index)
    factor_panel = factor_panel.loc[index]
    forward_panel = forward_panel_full.reindex(index)
    price_panel = open_panel.loc[index]
    exposure_panel = np.log(amount_panel.loc[index].where(amount_panel.loc[index] > 0))

    neutral_panel = neutralize_panel(factor_panel, exposure_panel).reindex(factor_panel.index)

    raw_corr = factor_panel.corrwith(exposure_panel, axis=1, method="spearman").mean()
    net_corr = neutral_panel.corrwith(exposure_panel, axis=1, method="spearman").mean()

    print(f"factor=mom_20d  exposure=log(amount)  horizon={HORIZON}  quantiles={QUANTILES}")
    print(f"与暴露的横截面秩相关：raw={raw_corr:+.3f}  ->  neutralized={net_corr:+.3f}")
    print()
    print(f"{'':<12} {'IC':>8} {'t(NW)':>7}  {'spread':>8} {'t(NW)':>7}  {'total':>8}  {'sharpe':>6}")
    report("raw", factor_panel, forward_panel, price_panel)
    report("neutralized", neutral_panel, forward_panel, price_panel)

if __name__ == "__main__":
    main()