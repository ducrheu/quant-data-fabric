from datetime import datetime

import pytest

from src.domain.financial import FinancialRecord
from src.repositories.financial import FinancialRepository


@pytest.fixture
def repository(tmp_path):
    db_path = tmp_path / "test.duckdb"
    repo = FinancialRepository(str(db_path))

    yield repo

    repo.close()


def test_save_is_idempotent(repository):
    record = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=80000000000,
        event_time=datetime(2025, 12, 31),
        available_time=datetime(2026, 4, 30),
        processing_time=datetime(2026, 5, 1),
        source="tushare",
        revision_id=1,
    )

    repository.save(record)
    repository.save(record)

    count = repository.con.execute(
        """
        SELECT COUNT(*)
        FROM financial_fact
        WHERE symbol = ?
          AND metric_name = ?
        """,
        ["600519.SH", "net_income"],
    ).fetchone()[0]

    assert count == 1


def test_pit_query_returns_latest_available_version(repository):
    record_v1 = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=80000000000,
        event_time=datetime(2025, 12, 31),
        available_time=datetime(2026, 4, 30),
        processing_time=datetime(2026, 5, 1),
        source="tushare",
        revision_id=1,
    )

    record_v2 = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=78000000000,
        event_time=datetime(2026, 12, 31),
        available_time=datetime(2026, 4, 30),
        processing_time=datetime(2026, 5, 1),
        source="tushare",
        revision_id=2,
    )

    repository.save(record_v1)
    repository.save(record_v2)

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 5, 10),
    )

    assert result is not None
    assert result[2] == 78000000000

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 5, 25),
    )

    assert result is not None
    assert result[2] == 78000000000
