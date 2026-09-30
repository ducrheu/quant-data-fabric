import numpy as np
import pandas as pd
import pytest

from src.factors.backtest import(
    annualized_return,
    backtest,
    bucket_labels,
    cumulative_net,
    execution_returns,
    max_drawdown,
    one_way_turnover,
    rebalance_periods,
    sharpe,
)

def test_rebalance_periods_are_contiguous_and_non_overlapping():
    periods = rebalance_periods(100, 20)

    assert periods[0] == (0, 1, 21)
    assert periods[1] == (20, 21, 41)

    for (_, _, exit_idx), (_, next_entry_idx, _) in zip(periods, periods[1:]):
        assert exit_idx == next_entry_idx


@pytest.mark.parametrize("step", [0, -1])
def test_rebalance_periods_reject_non_positive_step(step):
    with pytest.raises(ValueError):
        rebalance_periods(100, step)

def test_execution_returns_use_entry_and_exit_prices():
    panel = pd.DataFrame(
        {"A": [1.0, 2.0, 4.0], "B": [10.0, 10.0,  5.0]},
        index = pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
    )

    result = execution_returns(panel, entry_idx=1, exit_idx=2)

    assert result["A"] == pytest.approx(1.0)
    assert result["B"] == pytest.approx(-0.5)

def test_bucket_labels_put_lowest_values_in_bucket_zero():
    values = pd.Series([5.0, 1.0, 3.0, 2.0], index=list("abcd"))

    labels = bucket_labels(values, 2)

    assert labels["b"] == 0
    assert labels["d"] == 0
    assert labels["c"] == 1
    assert labels["a"] == 1

def test_one_way_turnover_counts_new_names():
    assert one_way_turnover(set(), {"A", "B"}) == 1.0
    assert one_way_turnover({"A", "B"}, {"A", "B"}) == 0.0
    assert one_way_turnover({"A", "B"}, {"A", "C"}) == 0.5
    assert one_way_turnover({"A", "B"}, set()) == 0.0

def test_cumulative_net_compounds():
    net = cumulative_net(pd.Series([0.10, 0.10]))

    assert net.iloc[-1] == pytest.approx(1.21)

def test_max_drawdown_measure_peak_to_trough():
    net = pd.Series([1.0, 1.20, 0.90, 1.10])

    assert max_drawdown(net) == pytest.approx(0.25)

def test_sharpe_scales_with_square_root_of_periods_per_year():
    returns = pd.Series([0.02, 0.00, 0.01, 0.03])

    assert sharpe(returns, 48) == pytest.approx(sharpe(returns, 12) * 2.0)

def test_annualized_return_folds_periods_into_a_year():
    assert annualized_return(0.10, n_periods=2, periods_per_year=4) == pytest.approx(0.21)

def test_backtest_is_non_overlapping_and_reports_turnover():
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    symbols = ["S0", "S1", "S2", "S3"]

    factor_panel = pd.DataFrame([[0.0, 1.0, 2.0, 3.0]] * 5, index=dates, columns=symbols)
    price_panel = pd.DataFrame(
        [
            [1.00, 1.00, 1.00, 1.00],
            [1.00, 1.00, 1.00, 1.00],
            [0.90, 0.90 ,1.10, 1.10],
            [0.81, 0.81, 1.21, 1.21],
            [0.73, 0.73, 1.33, 1.33],
        ],
        index=dates,
        columns=symbols,
    )

    result = backtest(factor_panel, price_panel, step=2, n_quantiles=2)

    assert len(result) == 1
    assert result["long"].iloc[0] == pytest.approx(0.21)
    assert result["short"].iloc[0] == pytest.approx(-0.19)
    assert result["spread"].iloc[0] == pytest.approx(0.40)
    assert result["turnover"].iloc[0] == pytest.approx(1.0)
    assert len(rebalance_periods(5, 1)) == 3