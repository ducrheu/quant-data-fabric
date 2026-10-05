"""Manual research script: backtest the momentum factor (non-overlapping).

与 run_analysis.py 的分工：
- run_analysis.py 回答"因子里有没有信息"（IC / 分位 / 多空价差）
- 本脚本回答"拿它交易会怎样"（净值 / 年化 / Sharpe / 回撤 / 换手）

口径：
- 每 HORIZON 个交易日调一次仓，**非重叠**（信号频率 = 持有期）
- 信号在调仓日收盘后得到，**次日开盘成交**（杜绝未来函数）
- 等权多空（Q5 多、Q1 空），0 成本，但报出换手率
"""

import duckdb
import pandas as pd

from src.config import FACTOR_DB_PATH, PRICE_DB_PATH
from src.factors.backtest import (
annualized_return, backtest, cumulative_net, max_drawdown, sharpe,
)

FACTOR_NAME = "mom_20d"
HORIZON = 20
QUANTILES = 5
TRADING_DAYS_PER_YEAR = 252
PERIODS_PER_YEAR = TRADING_DAYS_PER_YEAR / HORIZON
EXECUTION_PRICE = "open"

def load_panels():
    """读出因子与价格，各自透视成 (交易日 × 股票) 的面板。"""
    price_con = duckdb.connect(PRICE_DB_PATH, read_only=True)
    prices = price_con.execute(
        f"""
        SELECT symbol, trade_time, {EXECUTION_PRICE} AS price
        FROM price_daily
        ORDER BY symbol, trade_time
        """
    ).fetch_df()
    price_con.close()

    factor_con = duckdb.connect(FACTOR_DB_PATH, read_only=True)
    factors = factor_con.execute(
        """
        SELECT symbol, trade_time, value
        FROM factor_daily
        WHERE factor_name = ?
        ORDER BY symbol, trade_time
        """,
        [FACTOR_NAME],
    ).fetch_df()
    factor_con.close()

    return factors, prices

def main():
    factors, prices = load_panels()

    factor_panel = factors.pivot(index="trade_time", columns="symbol", values="value")
    price_panel = prices.pivot(index="trade_time", columns="symbol", values="price")

    # 两个面板必须共用同一套交易日序号，否则下标会对错
    common_dates = factor_panel.index.intersection(price_panel.index)
    factor_panel = factor_panel.loc[common_dates]
    price_panel = price_panel.loc[common_dates]

    result = backtest(factor_panel, price_panel, step=HORIZON, n_quantiles=QUANTILES)

    net = cumulative_net(result["spread"])
    total = float(net.iloc[-1] - 1.0)
    n_periods = len(result)

    print(
        f"factor={FACTOR_NAME} step={HORIZON} quantiles={QUANTILES}"
        f"price={EXECUTION_PRICE}"
    )

    print(f"dates={len(common_dates)} symbol={factor_panel.shape[1]} periods={n_periods} ")
    print()
    print("=== per-period long-short (Q5 - Q1) ===")
    for _, row in result.iterrows():
        print(
            f" {row['trade_time']:%Y%m%d} long={row['long']:+.4f} "
            f"short={row['short']:+.4f} spread={row['spread']:+.4f} "
            f"turnover={row['turnover']:.2f} "
        )
    print()
    print("=== summary ===")
    print(f"total return       : {total:+.2%}")
    print(f"annualized return  : {annualized_return(total, n_periods, PERIODS_PER_YEAR):+.2%}")
    print(f"sharpe (annualized): {sharpe(result['spread'], PERIODS_PER_YEAR):+.2f}")
    print(f"max drawdown       : {max_drawdown(net):.2%}")
    print(f"mean turnover      : {result['turnover'].mean():.2%}")
    print(f"win rate           : {(result['spread'] > 0).mean():.1%}")
    print()
    print(
        f"! 独立周期数只有 {n_periods}（{len(common_dates)} 个交易日 / {HORIZON}），"
        f"年化与 Sharpe 都是小样本估计。"
    )
    print(
        f"! 未计交易成本；按平均换手 {result['turnover'].mean():.2%} 估算，"
        f"每期成本 ~= 换手 x 2 x 单边费率。"
    )
    print("! 价格为未复权，除权除息会造成假信号。")

if __name__ == "__main__":
    main()