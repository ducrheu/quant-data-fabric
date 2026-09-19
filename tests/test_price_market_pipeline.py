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

def make_row(ts_code, trade_date):
    return {**GOOD_ROW, "ts_code": ts_code, "trade_date": trade_date}

class FakeMarketClient:
    """Fake client for that only supports whole_market pulls (trade_date)"""

    def __init__(self, rows_by_date):
        self.rows_by_date = rows_by_date
        self.calls = []

    def daily(self, trade_date):
        self.calls.append(trade_date)
        return pd.DataFrame(self.rows_by_date.get(trade_date, []))

def make_pipeline(tmp_path, rows_by_date):
    client = FakeMarketClient(rows_by_date)
    connector = TusharePriceConnector(client)
    normalizer = TusharePriceNormalizer()
    repository = PriceRepository(str(tmp_path / "price.duckdb"))
    return PricePipeline(connector, normalizer, repository), repository, client

def test_market_run_keeps_only_universe(tmp_path):
    rows_by_date = {
        "20260109": [
            make_row("600519.SH", "20260109"),
            make_row("000858.SZ", "20260109"),
            make_row("999999.SZ", "20260109")
        ],
    }
    pipeline, repository, client = make_pipeline(tmp_path, rows_by_date)
    universe = {"600519.SH", "000858.SZ"}

    first = pipeline.run_market("20260109", universe)
    second = pipeline.run_market("20260109", universe)

    stored = repository.con.execute(
        "SELECT SYMBOL, COUNT(*) FROM price_daily GROUP BY symbol ORDER BY symbol"
    ).fetchall()
    repository.close()

    assert first.total == 2
    assert first.market_rows == 3
    assert first.saved == 2
    assert second.saved == 0
    assert second.skipped == 2
    assert stored == [("000858.SZ", 1), ("600519.SH", 1)]

def test_market_run_counts_bad_rows_as_failed(tmp_path):
    rows_by_date = {
        "20260109": [
            make_row("600519.SH", "20260109"),
            {**make_row("000858.SZ", "20260109"), "high": 1.0, "low": 2000.0},
        ],
    }
    pipeline, repository, _ = make_pipeline(tmp_path, rows_by_date)

    result = pipeline.run_market("20260109", {"600519.SH", "000858.SZ"})
    rows_in_db = repository.con.execute(
        "SELECT COUNT(*) FROM price_daily"
    ).fetchone()[0]
    repository.close()

    assert result.total == 2
    assert result.saved == 1
    assert result.failed == 1
    assert rows_in_db == 1
    assert any("(business)" in e for e in result.errors)

def test_market_run_handles_empty_day(tmp_path):
    pipeline, repository, client = make_pipeline(tmp_path, {})

    result = pipeline.run_market("20260110", {"600519.SH"})
    repository.close()

    assert result.total == 0
    assert result.saved == 0
    assert result.market_rows == 0
    assert client.calls == ["20260110"]