from datetime import datetime

import pytest

from src.domain.price import PriceRecord
from src.factors.momentum import compute_momentum

def make_bar(day: int, close: float) -> PriceRecord:
    return PriceRecord(
        symbol = "600519.SH",
        trade_time = datetime(2026, 1, day),
        open = close,
        high = close,
        low = close,
        close = close,
        volume = 1000.0,
        source = "tushare",
    )

def test_momentum_skips_warmup_period():
    bars = [make_bar(day, 100.0) for day in range(1, 6)]

    factors = compute_momentum(bars, window = 3)

    assert len(factors) == 2
    assert factors[0].trade_time == datetime(2026, 1, 4)
    assert factors[1].trade_time == datetime(2026, 1, 5)

def test_momentum_value():
    bars = [make_bar(1, 100.0), make_bar(2, 110.0)]

    factors = compute_momentum(bars, window = 1)

    assert len(factors) == 1
    assert factors[0].factor_name == "mom_1d"
    assert factors[0].value == pytest.approx(0.1)

def test_momentum_rejects_bad_window():
    with pytest.raises(ValueError):
        compute_momentum([], window = 0)