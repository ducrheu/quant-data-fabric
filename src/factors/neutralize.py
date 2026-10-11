"""因子中性化：把与某个暴露相关的部分剔掉，看剩余部分还有没有信息。

纯函数：输入 Series / DataFrame，不碰数据库、不碰文件。

做法是横截面 OLS：把因子对暴露回归，取残差作为新因子。

    factor_i = alpha + beta * exposure_i + residual_i

    neutral_i = residual_i

残差与暴露在横截面上正交（相关系数为 0）——这就是"剔除暴露"的严谨定义。
"""

import numpy as np
import pandas as pd

def neutralize(factor: pd.Series, exposure: pd.Series) -> pd.Series:
    """单个横截面：对exposure 做 OLS，返回残差"""
    data = pd.concat(
        [factor.rename("factor"), exposure.rename("exposure")],
        axis = 1
    ).dropna()

    if len(data) < 3:
        raise ValueError("need at least 3 observations to neutralize")

    y = data["factor"].to_numpy(dtype=float)
    x = data["exposure"].to_numpy(dtype=float)

    design = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coefficients

    return pd.Series(residual, index=data.index)

def neutralize_panel(factor_panel: pd.DataFrame, exposure_panel: pd.DataFrame) -> pd.DataFrame:
    """逐日横截面中性化，返回残差面板"""
    residuals = {}
    for date in factor_panel.index:
        try:
            residuals[date] = neutralize(factor_panel.loc[date], exposure_panel.loc[date])
        except ValueError:
            continue

    if not residuals:
        raise ValueError("no date had enough observations to neutralize")

    return pd.DataFrame(residuals).T