"""按交易日的摄入日志：一次API调用 = 一天 = 一条记录。"""

from datetime import date, datetime

import duckdb

from src.config import PRICE_DB_PATH


class IngestLogRepository:

    def __init__(self, db_path: str = PRICE_DB_PATH):
        self.con = duckdb.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_log
            (
            trade_date DATE NOT NULL,
            source VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            market_rows INTEGER,
            kept INTEGER,
            saved INTEGER,
            skipped INTEGER,
            failed INTEGER,
            error VARCHAR,
            finished_at TIMESTAMP NOT NULL,
                
            UNIQUE (trade_date, source)
            )
            """
        )

    def record(
            self,
            trade_date: date,
            source: str,
            status: str,
            market_rows: int,
            kept: int,
            saved: int,
            skipped: int,
            failed: int,
            error: str | None = None,
    ) -> None:
        self.con.execute(
            """
            INSERT INTO ingest_log
                (trade_date, source, status, market_rows, kept, 
                 saved, skipped, failed, error, finished_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (trade_date, source) DO UPDATE SET
                    status = EXCLUDED.status,
                    market_rows = EXCLUDED.kept,
                    kept = EXCLUDED.kept,
                    saved = EXCLUDED.saved,
                    skipped = EXCLUDED.skipped,
                    failed = EXCLUDED.failed,
                    error = EXCLUDED.error,
                    finished_at = EXCLUDED.finished_at
            """,
            [trade_date, source, status, market_rows, kept,
             saved, skipped, failed, error, datetime.now(),
             ],
        )

    def done_dates(self, source: str) -> set[date]:
        """已成功摄入的交易日，重跑时跳过这些日期"""
        rows = self.con.execute(
            """
            SELECT trade_date FROM ingest_log
                WHERE source = ? AND status = 'success'
            """,
            [source],
        ).fetchall()
        return {row[0] for row in rows}

    def close(self):
        self.con.close()