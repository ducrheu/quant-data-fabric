"""Momentum factor: N-day cumulative return."""

import pandas as pd

from src.domain.factor import FactorRecord
from src.domain.price import PriceRecord

def compute_momentum(bars: list[PriceRecord], window: int) -> list[FactorRecord]:

    if window <= 0:
        raise ValueError("window must be positive")

    records = []
    for index in range(window, len(bars)):
        current = bars[index]
        past = bars[index - window]

        value = current.close / past.close - 1.0

        records.append(
            FactorRecord(
                symbol = current.symbol,
                factor_name = f"mom_{window}d",
                trade_time=current.trade_time,
                value = value,
            )
        )
    return records

def momentum_frame(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """从长表（symbol / trade_time / close）算动量，返回 (symbol, trade_time, value)。

    关键：按 **每只股票自己的 bar 序列** 移位，而不是按整个面板的行号移位。
    两者在有停牌缺口的票上结果不同 —— 前者才是 compute_momentum 的定义。
    """
    if window <= 0:
        raise ValueError("window must be positive")

    frame = prices[["symbol", "trade_time", "close"]].copy()
    frame["value"] = frame["close"] / frame.groupby("symbol")["close"].shift(window) - 1.0

    return frame.dropna(subset=["value"])[["symbol", "trade_time", "value"]].reset_index(drop=True)


def forward_return_frame(prices: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """前瞻收益：同样按各股自己的 bar 序列移位，与 momentum_frame 保持同一约定。"""
    if horizon <= 0:
        raise ValueError("horizon must be positive")

    frame = prices[["symbol", "trade_time", "close"]].copy()
    frame["value"] = frame.groupby("symbol")["close"].shift(-horizon) / frame["close"] - 1.0

    return frame.dropna(subset=["value"])[["symbol", "trade_time", "value"]].reset_index(drop=True)
