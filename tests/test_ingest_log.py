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

def test_record_upsert_keeps_market_rows(tmp_path):
    repo = IngestLogRepository(str(tmp_path / "log.duckdb"))
    day = date(2025, 1, 2)

    repo.record(day, "tushare", "success", market_rows = 5550,
                kept = 297, saved = 297, skipped = 0, failed = 0)
    repo.record(day, "tushare", "success", market_rows = 5553,
                kept = 297, saved = 297, skipped = 0, failed = 0)

    result = repo.con.execute(
        "SELECT market_rows, kept FROM ingest_log WHERE trade_date = ? AND source = ?",
        [day, "tushare"],
    ).fetchone()
    repo.close()

    assert result == (5553, 297)