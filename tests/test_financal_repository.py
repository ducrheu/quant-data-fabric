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
        event_time=datetime(2025, 12, 31),
        available_time=datetime(2026, 5, 30),
        processing_time=datetime(2026, 6, 1),
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
    assert result[2] == 80000000000

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 7, 1),
    )

    assert result is not None
    assert result[2] == 78000000000

def test_pit_result_does_not_depend_on_insert_order(repository):
    v1 = FinancialRecord(
        symbol = "600519.SH",
        metric_name = "net_income",
        value = 80000000000,
        event_time = datetime(2025, 12, 31),
        available_time = datetime(2026, 4, 30),
        processing_time = datetime(2026, 5, 1),
        source = "tushare",
        revision_id = 1,
    )

    v2 = FinancialRecord(
        symbol = "600519.SH",
        metric_name = "net_income",
        value = 78000000000,
        event_time = datetime(2025, 12, 31),
        available_time = datetime(2026, 5, 30),
        processing_time = datetime(2026, 6, 1),
        source = "tushare",
        revision_id = 2,
    )

    repository.save(v2)
    repository.save(v1)

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 7, 1)
    )

    assert result is not None
    assert result[2] == 78000000000

def test_pit_tracks_multiple_report_periods(repository):
    report_2024 = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=70000000000,
        event_time=datetime(2024, 12, 31),
        available_time=datetime(2025, 4, 20),
        processing_time=datetime(2025, 4, 21),
        source="tushare",
        revision_id=1,
    )

    report_2025_v1 = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=80000000000,
        event_time=datetime(2025, 12, 31),
        available_time=datetime(2026, 4, 30),
        processing_time=datetime(2026, 5, 1),
        source="tushare",
        revision_id=1,
    )

    report_2025_v2 = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=78000000000,
        event_time=datetime(2025, 12, 31),
        available_time=datetime(2026, 6, 15),
        processing_time=datetime(2026, 6, 16),
        source="tushare",
        revision_id=2,
    )

    repository.save(report_2025_v2)
    repository.save(report_2024)
    repository.save(report_2025_v1)

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2025, 5, 1),
    )
    assert result is not None
    assert result[2] == 70000000000

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 5, 10),
    )
    assert result is not None
    assert result[2] == 80000000000

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 7, 1),
    )
    assert result is not None
    assert result[2] == 78000000000

def test_get_pit_return_none_when_event_not_available_yet(repository):
    report_2025 = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=80000000000,
        event_time=datetime(2025, 12, 31),
        available_time=datetime(2026, 4, 30),
        processing_time=datetime(2026, 5, 1),
        source="tushare",
        revision_id=1,
    )

    repository.save(report_2025)

    result = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 3, 1),
        event_time = datetime(2025, 12, 31),
    )

    assert result is None


def test_save_returns_inserted_count(repository):
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
    first = repository.save(record)
    second = repository.save(record)

    assert first == 1
    assert second == 0