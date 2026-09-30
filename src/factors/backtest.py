"""回测骨架：把"因子有没有信息"变成"拿它交易会怎样"。

纯函数 = 输入 DataFrame / Series，输出数字或 Series，不碰数据库、不碰文件。
所以测试不需要任何真实数据。

两条正确性底线：
- **不重叠**：调仓周期首尾相接、互不重叠（信号频率 = 持有期）
- **不穿越**：成交价严格晚于信号日（t 日收盘出信号 → t+1 成交），杜绝未来函数
"""

import numpy as np
import pandas as pd


def rebalance_periods(n_dates: int, step: int) -> list[tuple[int, int, int]]:
    """列出非重叠的调仓周期 [(signal_idx, entry_idx, exit_idx), ...]。

    下标是**交易日序号**（不是日期）：
    - signal_idx = 调仓日，因子在这一天收盘后才可得
    - entry_idx  = signal_idx + 1，成交日（严格晚于信号日）
    - exit_idx   = signal_idx + step + 1，平仓日

    相邻周期首尾相接：第 k 期的 exit_idx 等于第 k+1 期的 entry_idx，
    因此持仓不重叠——这就是"信号频率 = 持有期"。
    """
    if step <= 0:
        raise ValueError("step must be greater than 0")

    periods = []
    k = 0
    while True:
        signal_idx = k * step
        entry_idx = signal_idx + 1
        exit_idx = signal_idx + step + 1
        if exit_idx >= n_dates:
            break
        periods.append((signal_idx, entry_idx, exit_idx))
        k += 1

    return periods


def execution_returns(panel: pd.DataFrame, entry_idx: int, exit_idx: int) -> pd.Series:
    """从 (交易日 × 股票) 的价格面板取两个下标，算区间收益。

    用成交价算收益（不是信号日的收盘价），是"不穿越"的落地。
    """
    return panel.iloc[exit_idx] / panel.iloc[entry_idx] - 1.0


def bucket_labels(values: pd.Series, n_quantiles: int) -> pd.Series:
    """横截面等分 n_quantiles 组，返回组号（0 = 因子最小）。"""
    if n_quantiles < 2:
        raise ValueError("n_quantiles must be at least 2")

    return pd.qcut(values.rank(method="first"), n_quantiles, labels=False)


def one_way_turnover(previous: set, current: set) -> float:
    """单边换手率：当前持仓里有多大比例是新买入的。"""
    if not current:
        return 0.0
    if not previous:
        return 1.0
    return len(current - previous) / len(current)


def cumulative_net(returns: pd.Series) -> pd.Series:
    """逐期收益率连乘成净值曲线（起点 1.0）。"""
    return (1.0 + returns).cumprod()


def annualized_return(total_return: float, n_periods: int, periods_per_year: float) -> float:
    """几何年化：把 n_periods 期的总收益折算到一年。"""
    if n_periods <= 0:
        raise ValueError("n_periods must be positive")

    return float((1.0 + total_return) ** (periods_per_year / n_periods) - 1.0)


def sharpe(returns: pd.Series, periods_per_year: float) -> float:
    """期频 Sharpe 年化：均值 / 标准差 × √(每年期数)。"""
    values = returns.dropna()
    if len(values) < 2:
        raise ValueError("need at least 2 values")

    return float(values.mean() / values.std(ddof=1) * np.sqrt(periods_per_year))


def max_drawdown(net: pd.Series) -> float:
    """最大回撤（正数）：净值从历史高点回落的最大幅度。"""
    peak = net.cummax()
    return float(-((net - peak) / peak).min())

def backtest(
        factor_panel: pd.DataFrame,
        price_panel: pd.DataFrame,
        step: int,
        n_quantiles: int = 5,
) -> pd.DataFrame:
    """逐期回测，返回每期的多头 / 空头 / 多空收益与换手。

    两个面板都是 (交易日 × 股票) 的透视表，索引为升序交易日。
    """
    periods = rebalance_periods(len(price_panel), step)

    rows = []
    previous_long: set = set()
    previous_short: set = set()

    for signal_idx, entry_idx, exit_idx in periods:
        factor = factor_panel.iloc[signal_idx].dropna()
        returns = execution_returns(price_panel, entry_idx, exit_idx)

        common = factor.index.intersection(returns.index)
        factor = factor.loc[common]
        returns = returns.loc[common]

        buckets = bucket_labels(factor, n_quantiles)
        long_mask = buckets == n_quantiles - 1
        short_mask = buckets == 0

        long_set = set(factor[long_mask].index)
        short_set = set(factor[short_mask].index)

        rows.append(
            {
                "trade_time": price_panel.index[signal_idx],
                "long": returns[long_mask].mean(),
                "short": returns[short_mask].mean(),
                "spread": returns[long_mask].mean() - returns[short_mask].mean(),
                "turnover": (
                    one_way_turnover(previous_long, long_set) + one_way_turnover(previous_short, short_set)
                ) / 2.0,
            }
        )
        previous_long = long_set
        previous_short = short_set
    return pd.DataFrame(rows)