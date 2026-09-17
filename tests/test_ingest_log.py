from datetime import date

from src.repositories.ingest_log import IngestLogRepository

def test_done_dates_returns_only_success(tmp_path):
    log = IngestLogRepository(str(tmp_path / "price.duckdb"))

    log.record(date(2025, 1, 3), "tushare", "failed", 0, 0, 0, 0, 0, error = "timeout")
    log.record(date(2025, 1, 2), "tushare", "success", 5550, 300, 300, 0, 0)

    assert log.done_dates("tushare") == {date(2025, 1, 2)}
    log.close()

def test_record_overwrites_same_day(tmp_path):
    log = IngestLogRepository(str(tmp_path / "price.duckdb"))

    log.record(date(2025, 1, 2), "tushare", "failed", 0, 0, 0, 0, 0, error = "timeout")
    log.record(date(2025, 1, 2), "tushare", "success", 5550, 300, 300, 0, 0)

    rows = log.con.execute(
        "SELECT status, saved FROM ingest_log WHERE trade_date = ?",
        [date(2025, 1, 2)],
    ).fetchall()
    log.close()

    assert rows == [("success", 300)]