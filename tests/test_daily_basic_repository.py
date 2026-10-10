from datetime import datetime

import pytest

from src.domain.daily_basic import DailyBasicRecord
from src.repositories.daily_basic import DailyBasicRepository


@pytest.fixture
def repository(tmp_path):
    repo = DailyBasicRepository(str(tmp_path / "test.duckdb"))
    yield repo
    repo.close()

def make_record(**overrides):
    values = {
        "symbol": "600519.SH",
        "trade_time": datetime(2025, 9, 5),
        "close": 1500.0,
        "turnover_rate": 0.5,
        "total_mv": 1.8e8,
        "circ_mv": 1.8e8,
        "pe_ttm": 20.0,
        "pb": 8.0,
        "source": "tushare.daily_basic",
    }
    values.update(overrides)
    return DailyBasicRecord(**values)

def test_save_many_insert_records(repository):
    inserted = repository.save_many([make_record(), make_record(symbol="000001.SZ")])

    assert inserted == 2

def test_save_many_is_idempotent(repository):
    repository.save_many([make_record()])

    second = repository.save_many([make_record()])

    count = repository.con.execute("SELECT COUNT(*) FROM daily_basic").fetchone()[0]

    assert second == 0
    assert count == 1

def test_save_many_tolerates_missing_values(repository):
    inserted = repository.save_many([make_record(pe_ttm=None, pb=None)])

    assert inserted == 1