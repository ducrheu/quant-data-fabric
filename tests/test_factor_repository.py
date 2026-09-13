from datetime import datetime

import pytest

from src.domain.factor import FactorRecord
from src.repositories.factor import FactorRepository

@pytest.fixture
def repository(tmp_path):
    db_path = tmp_path / "factor_test.duckdb"
    repo = FactorRepository(str(db_path))

    yield repo

    repo.close()

def make_factor(day: int, name: str = "mom_20d", value: float = 0.1) -> FactorRecord:
    return FactorRecord(
        symbol = "600519.SH",
        factor_name = name,
        trade_time = datetime(2026, 1, day),
        value = value,
    )

def test_save_is_idempotent_and_returns_inserted_count(repository):
    record = make_factor(9)

    first = repository.save(record)
    second = repository.save(record)

    assert first == 1
    assert second == 0

def test_get_series_returns_ascending_records(repository):
    repository.save(make_factor(9, value = 0.09))
    repository.save(make_factor(7, value = 0.07))
    repository.save(make_factor(8, name = "mom_60d", value = 0.08))

    series = repository.get_series(
        "600519.SH",
        "mom_20d",
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )

    assert len(series) == 2
    assert series[0].trade_time == datetime(2026, 1, 7)
    assert series[1].trade_time == datetime(2026, 1, 9)