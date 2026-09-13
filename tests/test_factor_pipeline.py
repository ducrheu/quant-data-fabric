from datetime import datetime

from src.domain.price import PriceRecord
from src.pipelines.factor import MomentumFactorPipeline
from src.repositories.factor import FactorRepository
from src.repositories.price import PriceRepository

def make_bar(day: int, close: float) -> PriceRecord:
    return PriceRecord(
        symbol = "600519.SH",
        trade_time = datetime(2026, 1, day),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000.0,
        source="tushare",
    )

def make_pipeline(tmp_path):
    price_repo = PriceRepository(str(tmp_path / "price.duckdb"))
    factor_repo = FactorRepository(str(tmp_path / "factor.duckdb"))
    pipeline = MomentumFactorPipeline(price_repo, factor_repo)
    return pipeline, price_repo, factor_repo

def test_pipeline_uses_history_before_start(tmp_path):
    pipeline, price_repo, factor_repo = make_pipeline(tmp_path)

    closes = [100.0, 110.0, 121.0, 133.1, 146.41]
    for day, close in enumerate(closes, start=1):
        price_repo .save(make_bar(day, close))

    result = pipeline.run(
        "600519.SH",
        datetime(2026, 1, 4),  # 只输出最后两天
        datetime(2026, 1, 5),
        window=1,
    )

    assert result.total == 2
    assert result.saved == 2
    assert result.skipped == 0

def test_pipeline_second_run_skips_existing_factors(tmp_path):
    pipeline, price_repo, factor_repo = make_pipeline(tmp_path)

    for day, close in enumerate([100.0, 110.0, 121.0], start = 1):
        price_repo.save(make_bar(day, close))

    first = pipeline.run(
        "600519.SH", datetime(2026, 1, 1), datetime(2026, 1, 3), window = 1
    )
    second = pipeline.run(
        "600519.SH", datetime(2026, 1, 1), datetime(2026, 1, 3), window = 1
    )

    price_repo.close()
    factor_repo.close()

    assert first.saved == 2
    assert second.saved == 0
    assert second.skipped == 2