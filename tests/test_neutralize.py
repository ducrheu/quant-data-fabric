import numpy as np
import pandas as pd
import pytest

from src.factors.neutralize import neutralize, neutralize_panel

def test_neutralize_removes_pure_exposure():
    exposure = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    factor = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])

    residual = neutralize(factor, exposure)

    assert residual.abs().max() == pytest.approx(0.0, abs=1e-9)

def test_neutralize_keep_the_orthogonal_part():
    exposure = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    factor = pd.Series([1.0, 2.0, 3.0, 4.0, 6.0])

    residual = neutralize(factor, exposure)

    assert residual.mean() == pytest.approx(0.0, abs=1e-9)
    assert residual.corr(exposure) == pytest.approx(0.0, abs=1e-9)

def test_neutralize_ignores_missing_pairs():
    exposure = pd.Series([1.0, 2.0, 3.0, np.nan])
    factor = pd.Series([2.0, 4.0, 6.0, 9.0])

    residual = neutralize(factor, exposure)

    assert len(residual) == 3
    assert residual.abs().max() == pytest.approx(0.0, abs=1e-9)

def test_neutralize_reject_too_few_observation():
    with pytest.raises(ValueError):
        neutralize(pd.Series([1,0, 2.0]), pd.Series([1.0, 2.0]))

def test_neutralize_panel_handle_each_date_separately():
    dates = pd.date_range("2025-01-01", periods=2)
    symbols = list("abc")
    factor_panel = pd.DataFrame(
        [[1.0, 2.0, 3.0], [3.0, 6.0, 9.0]], index=dates, columns=symbols
    )
    exposure_panel = pd.DataFrame(
        [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]], index=dates, columns=symbols
    )

    residual = neutralize_panel(factor_panel, exposure_panel)

    assert residual.shape == (2, 3)
    assert residual.abs().max().max() == pytest.approx(0.0, abs=1e-9)