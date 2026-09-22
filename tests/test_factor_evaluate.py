import pandas as pd
import pytest

from src.factors.evaluate import rank_ic, sample_every, t_stat, long_short_spread, quantile_returns

def make_data (factor_values, returns):
    return pd.DataFrame(
        {
            "trade_time": ["2025-01-02"] * len(factor_values),
            "value": factor_values,
            "forward_return": returns,
        }
    )

def test_rank_ic_is_one_when_orders_match():
    data = make_data([0.01, 0.02, 0.03, 0.04], [0.10, 0.20, 0.30, 0.40])
    assert rank_ic(data).iloc[0] == pytest.approx(1.0)

def test_rank_ic_is_minus_one_when_orders_reverse():
    data = make_data([0.01, 0.02, 0.03, 0.04], [0.40, 0.30, 0.20, 0.10])
    assert rank_ic(data).iloc[0] == pytest.approx(-1.0)

def test_rank_ic_ignores_extreme_value():
    normal = make_data([0.01, 0.02, 0.03, 0.04], [0.10, 0.20, 0.30, 0.40])
    extreme = make_data([0.01, 0.02, 0.03, 0.04], [0.10, 0.20, 0.30, 40.0])
    assert rank_ic(normal).iloc[0] == pytest.approx(rank_ic(extreme).iloc[0])

def test_t_stat_matches_hand_calculation():
    # [1,2,3,4] → mean=2.5, std(ddof=1)=1.29099, t = 2.5 / (1.29099 / √4) = 3.8730
    assert t_stat(pd.Series([1.0, 2.0, 3.0, 4.0])) == pytest.approx(3.8730, abs=1e-4)

def test_t_stat_need_two_observations():
    with pytest.raises(ValueError):
        t_stat(pd.Series([1.0]))

def test_sample_every_takes_fixed_step_from_start():
    series = pd.Series(range(10))
    assert list(sample_every(series, 3)) == [0, 3, 6, 9]
    assert list(sample_every(series, 20)) == [0]

def test_quantile_returns_splits_by_factor_value():

    values = [float(v) for v in range(1, 11)]
    data = make_data(values, [v / 100 for v in values])

    frame = quantile_returns(data, n_quantiles = 2)

    assert frame.iloc[0].tolist() == pytest.approx([0.03, 0.08])

def test_long_short_spread_is_high_minus_low():
    values = [float(v) for v in range(1, 11)]
    data = make_data(values, [(11 - v) / 100 for v in values])

    spread = long_short_spread(quantile_returns(data, n_quantiles = 2))

    assert spread.iloc[0] == pytest.approx(-0.05)

def test_quantile_returns_keeps_one_row_per_date():
    frame = quantile_returns(
        pd.DataFrame(
            {
                "trade_time": ["2025-01-02"] * 4 + ["2025-01-03"] * 4,
                "value": [1.0, 2.0, 3.0, 4.0] * 2,
                "forward_return": [0.01, 0.02, 0.03, 0.04] * 2,
            }
        ),
        n_quantiles = 2,
    )
    assert len(frame) == 2

def test_quantile_returns_rejects_single_group():
    with pytest.raises(ValueError):
        quantile_returns(make_data([0.01, 0.02], [0.10, 0.20]), n_quantiles = 1)