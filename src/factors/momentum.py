"""Momentum factor: N-day cumulative return."""

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