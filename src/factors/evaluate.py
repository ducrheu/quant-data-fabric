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

def sample_every(series: pd.Series, step: int) -> pd.Series:
    """从第一个观测起，每隔 step 个取一个（固定起点 = 结果可复现）。"""
    if step <= 0:
        raise ValueError("step must be greater than 0")
    return series.iloc[::step]