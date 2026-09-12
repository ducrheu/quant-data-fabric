from datetime import datetime
import pytest

from src.domain.price import PriceRecord
from src.repositories.price import PriceRepository

@pytest.fixture
def repository(tmp_path):
    db_path = tmp_path / "price_test.duckdb"
    repo = PriceRepository(str(db_path))

    yield repo
    repo.close()

def test_price_save_is_idempotent(repository):
    record = PriceRecord(
        symbol = "600519.SH",
        trade_time = datetime(2026, 1, 9),
        open = 1417.0,
        high = 1428.6,
        low = 1416.01,
        close = 1419.1,
        volume = 29847.74,
        source = "tushare",
    )

    repository.save(record)
    repository.save(record)

    count = repository.con.execute(
        """
        SELECT COUNT(*)
        FROM price_daily
        WHERE symbol = ?
            AND trade_time = ?
        """,
        ["600519.SH", datetime(2026, 1, 9)]
    ).fetchone()[0]

    assert count == 1
def test_price_save_allows_different_days(repository):
    day1 = PriceRecord(
        symbol = "600519.SH",
        trade_time = datetime(2026, 1, 9),
        open = 1417.0,
        high = 1428.6,
        low = 1416.01,
        close = 1419.1,
        volume = 29847.74,
        source = "tushare",
    )

    day2 = PriceRecord(
        symbol = "600519.SH",
        trade_time = datetime(2026, 1, 8),
        open = 1423.33,
        high = 1423.36,
        low = 1408.14,
        close = 1412.3,
        volume = 29134.54,
        source = "tushare",
    )

    repository.save(day1)
    repository.save(day2)

    count = repository.con.execute(
        "SELECT COUNT(*) FROM price_daily"
    ).fetchone()[0]

    assert count == 2

def test_save_returns_inserted_count(repository):
    record = PriceRecord(
        symbol="600519.SH",
        trade_time=datetime(2026, 1, 9),
        open=1417.0, high=1428.6, low=1416.01, close=1419.1,
        volume=29847.74, source="tushare",
    )

    first = repository.save(record)
    second = repository.save(record)

    assert first == 1
    assert second == 0

def test_get_range_returns_records_in_ascending_time(repository):
    for day in (9, 8, 7):
        repository.save(
            PriceRecord(
                symbol = "600519.SH",
                trade_time = datetime(2026, 1, day),
                open=1400.0, high=1430.0, low=1390.0, close=1419.1,
                volume = 29847.74, source = "tushare",
            )
        )

    bars = repository.get_range(
        "600519.SH",
        datetime(2026, 1, 7),
        datetime(2026, 1, 10),
    )

    assert len(bars) == 3
    assert bars[0].trade_time == datetime(2026, 1, 7)
    assert bars[2].trade_time == datetime(2026, 1, 9)