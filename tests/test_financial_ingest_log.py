import pytest

from src.repositories.financial_ingest_log import FinancialIngestLogRepository


@pytest.fixture
def log_repo(tmp_path):
    repo = FinancialIngestLogRepository(str(tmp_path / "financial.duckdb"))
    yield repo
    repo.close()


def test_done_keys_returns_request_keys(log_repo):
    log_repo.record("baostock", "sh.600519", 2024, 4, "success", saved=1)

    assert log_repo.done_keys("baostock") == {("sh.600519", 2024, 4)}


def test_empty_counts_as_done(log_repo):
    """空结果也算做完 —— 否则未上市的票会被永远重试"""
    log_repo.record("baostock", "sh.999999", 2024, 4, "empty")

    assert ("sh.999999", 2024, 4) in log_repo.done_keys("baostock")


def test_failed_is_not_done(log_repo):
    log_repo.record("baostock", "sh.600519", 2024, 4, "failed", error="network")

    assert log_repo.done_keys("baostock") == set()


def test_same_key_is_upserted_not_duplicated(log_repo):
    log_repo.record("baostock", "sh.600519", 2024, 4, "failed", error="network")
    log_repo.record("baostock", "sh.600519", 2024, 4, "success", saved=1)

    rows = log_repo.con.execute(
        "SELECT status, saved, error FROM financial_ingest_log"
    ).fetchall()

    assert rows == [("success", 1, None)]
