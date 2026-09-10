from datetime import datetime

import pandas as pd

from src.connectors.price_connector import TusharePriceConnector
from src.normalizers.price import TusharePriceNormalizer
from src.pipelines.price import PricePipeline
from src.repositories.price import PriceRepository

GOOD_ROW = {
    "ts_code": "600519.SH",
    "trade_date": "20260109",
    "open": 1417.0,
    "high": 1428.6,
    "low": 1416.01,
    "close": 1419.1,
    "pre_close": 1412.3,
    "change": 6.8,
    "pct_chg": 0.4815,
    "vol": 29847.74,
    "amount": 4243865.418,
}

class FakeTushareClient:
    def __init__(self, rows):
        self.rows = rows

    def daily(self, ts_code, start_date, end_date):
        return pd.DataFrame(self.rows)

def make_pipeline(tmp_path, rows):
    client = FakeTushareClient(rows)
    connector = TusharePriceConnector(client)
    normalizer = TusharePriceNormalizer()
    repository = PriceRepository(str(tmp_path / "price.duckdb"))
    pipeline = PricePipeline(connector, normalizer, repository)
    return pipeline, repository

def test_pipeline_saves_all_good_rows(tmp_path):
    rows = [
        GOOD_ROW,
        {**GOOD_ROW, "trade_date": "20260108"},
    ]
    pipeline, repository = make_pipeline(tmp_path, rows)

    result = pipeline.run("600519.SH", "20260101", "20260110")
    repository.close()

    assert result.total == 2
    assert result.saved == 2
    assert result.failed == 0
    assert result.errors == []

def test_pipeline_skips_format_error(tmp_path):
    rows = [
        GOOD_ROW,
        {**GOOD_ROW, "trade_date": "2026-01-09"},
    ]
    pipeline, repository = make_pipeline(tmp_path, rows)

    result = pipeline.run("600519.SH", "20260101", "20260110")
    repository.close()

    assert result.total == 2
    assert result.saved == 1
    assert result.failed == 1
    assert any("(format)" in e for e in result.errors)

def test_pipeline_skips_business_error(tmp_path):
    rows = [
        GOOD_ROW,
        {**GOOD_ROW, "high": 1400.0, "low": 1450.0},
    ]
    pipeline, repository = make_pipeline(tmp_path, rows)

    result = pipeline.run("600519.SH", "20260101", "20260110")
    repository.close()

    assert result.total == 2
    assert result.saved == 1
    assert result.failed == 1
    assert any("(business)" in e for e in result.errors)