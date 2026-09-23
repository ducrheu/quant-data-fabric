"""因子评价：把研究脚本里"看一眼"的逻辑变成可测试的纯函数。

纯函数 = 输入 DataFrame / Series，输出数字或 Series，不碰数据库、不碰文件。
所以测试不需要任何真实数据，几行构造数据就能跑。
"""

import numpy as np
import pandas as pd

def rank_ic(
        data: pd.DataFrame,
        date_col: str = "trade_time",
        factor_col: str = "value",
        return_col: str = "forward_return",
) -> pd.Series:
    """每个交易日的横截面秩相关（Spearman）。返回以交易日为索引的 Series。"""
    return data.groupby(date_col).apply(
        lambda group: group[factor_col].corr(group[return_col], method="spearman")
    )

def t_stat(series: pd.Series) -> float:
    """均值 / (标准差 / √n)。

    注意：只有序列的观测彼此独立时这个数才可信。
    重叠的前瞻收益（如 20 日窗口逐日计算）会严重高估 t 值。
    """
    values = series.dropna()
    if len(values) < 2:
        raise ValueError("need at least 2 values")

    return float(values.mean() / (values.std(ddof = 1) / np.sqrt(len(values))))

def newey_west_t_stat(series: pd.Series, max_lag: int) -> float:
    """均值 / Newey-West 长期标准误（Bartlett 权重）。

        普通 t 值假设观测彼此独立；20 日前瞻收益在相邻交易日共享 19 天，
        这个假设不成立，普通 t 值会严重虚高。
        这里保留全部样本，只把"相邻观测相关"这件事计入标准误。

        自协方差用 n - 1 归一化，好处是 max_lag = 0 时严格退化为 t_stat，
        这条性质本身就是一条测试。
        """
    if max_lag < 0:
        raise ValueError("max_lag must not be negative")

    values = series.dropna().to_numpy(dtype = float)
    n = len(values)
    if n < 2:
        raise ValueError("need at least 2 values")

    centered = values - values.mean()

    def autocovariance(lag: int) -> float:
        if lag == 0:
            return float(centered @ centered) / (n - 1)

        return float (centered[lag:] @ centered[:-lag]) / (n - 1)

    long_run_variance = autocovariance(0)

    for lag in range(1, min(max_lag, n - 1) + 1):
        weight = 1.0 - lag / (max_lag + 1)
        long_run_variance += 2.0 * weight * autocovariance(lag)

    variance_of_mean = long_run_variance / n
    if variance_of_mean <= 0:
        raise ValueError("non-positive long-run variance")

    return float(values.mean() / np.sqrt(variance_of_mean))

def sample_every(series: pd.Series, step: int) -> pd.Series:
    """从第一个观测起，每隔 step 个取一个（固定起点 = 结果可复现）。"""
    if step <= 0:
        raise ValueError("step must be greater than 0")
    return series.iloc[::step]

def quantile_returns(
        data: pd.DataFrame,
        n_quantiles: int = 5,
        date_col: str = "trade_time",
        factor_col: str = "value",
        return_col: str = "forward_return",
) -> pd.DataFrame:
    """每天按因子值切 n_quantiles 组，返回 (交易日 × 组号) 的收益均值表。

        组号 0 = 因子最低，n_quantiles - 1 = 因子最高。
        先横截面（当天各组）后时间序列（跨天平均），避免天数不均衡造成的权重失真。
        """
    if n_quantiles < 2:
        raise ValueError("n_quantiles must be at least 2")

    buckets = data.groupby(date_col)[factor_col].transform(
        lambda series: pd.qcut(series.rank(method = "first"), n_quantiles, labels = False)
    )

    per_date = data.assign(bucket = buckets).groupby([date_col, "bucket"])[return_col].mean()
    return per_date.unstack()

def long_short_spread(quantiles: pd.DataFrame) -> pd.Series:
    """最高组 − 最低组的日度价差序列（可交易性的第一近似，毛收益）。"""
    return quantiles[quantiles.columns[-1]] - quantiles[quantiles.columns[0]]