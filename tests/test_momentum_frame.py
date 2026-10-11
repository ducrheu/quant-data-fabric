from datetime import datetime

import pandas as pd
import pytest

from src.domain.price import PriceRecord
from src.factors.momentum import compute_momentum, momentum_frame


def make_bars(symbol, closes):
    start = datetime(2025, 1, 2)
    days = [start, start.replace(day=3), start.replace(day=6), start.replace(day=7)]
    return [
        PriceRecord(
            symbol=symbol, trade_time=day, open=c, high=c, low=c, close=c,
            volume=1.0, source="test",
        )
        for day, c in zip(days, closes)
    ]


def test_momentum_frame_matches_compute_momentum_with_gaps():
    a = make_bars("600519.SH", [100.0, 101.0, 102.0, 103.0])
    b = make_bars("000001.SZ", [10.0, 11.0, 11.5, 12.0])
    records = a + [r for r in b if r.trade_time.day != 6]

    frame = pd.DataFrame(
        [{"symbol": r.symbol, "trade_time": r.trade_time, "close": r.close} for r in records]
    )

    expected = []
    for symbol in ("600519.SH", "000001.SZ"):
        expected.extend(compute_momentum([r for r in records if r.symbol == symbol], 2))
    expected_frame = pd.DataFrame(
        [{"symbol": r.symbol, "trade_time": r.trade_time, "value": r.value} for r in expected]
    )

    got = momentum_frame(frame, 2).sort_values(["symbol", "trade_time"]).reset_index(drop=True)
    exp = expected_frame.sort_values(["symbol", "trade_time"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(got, exp)


@pytest.mark.parametrize("window", [0, -1])
def test_momentum_frame_rejects_non_positive_window(window):
    with pytest.raises(ValueError):
        momentum_frame(
            pd.DataFrame([{"symbol": "A", "trade_time": datetime(2025, 1, 2), "close": 1.0}]),
            window,
        )
