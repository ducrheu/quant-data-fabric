import pytest

from src.repositories.ingest_batch import IngestBatchRepository

@pytest.fixture
def batches(tmp_path):
    repo = IngestBatchRepository(str(tmp_path / "batch.duckdb"))
    yield repo
    repo.close()

def test_start_assigns_increasing_batch_id(batches):
    first = batches.start("tushare", "income", '{"ts_code": "600519.SH"}')
    second = batches.start("tushare", "income", '{"ts_code": "000001.SZ"}')

    assert first == 1
    assert second == 2

def test_start_leaves_batch_running(batches):
    batch_id = batches.start("tushare", "income", "{}")

    row = batches.get(batch_id)

    assert row[4] == "running"
    assert row[6] is None

def test_finish_records_count(batches):
    batch_id = batches.start("tushare", "income", "{}")

    batches.finish(
        batch_id, "success",
        total=3, saved=2, restated=1, skipped=1, failed=1,
    )

    row = batches.get(batch_id)

    assert row[4] == "success"
    assert row[6] is not None
    assert row[7] == 3
    assert row[8] == 2
    assert row[9] == 1

def test_get_returns_none_for_unknow_batch(batches):
    assert batches.get(999) is None