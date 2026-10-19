"""财务摄入日志：按 (source, code, year, quarter) 记账，用于季频回填的断点恢复。

与 ingest_log 的区别：
- ingest_log            UNIQUE (trade_date, source)            按交易日，行情 / 估值用
- financial_ingest_log  UNIQUE (source, code, year, quarter)   按"请求键"，财务季频用

与 ingest_batch 的区别（两者都保留，职责不同）：
- ingest_batch          一次 API 调用一行，记参数与耗时 —— 血缘 / 重放
- financial_ingest_log  某个请求键做完没              —— 断点恢复
  （所以"空结果"也必须记账，否则每次重跑都重复请求它）

stat_date 是**便利列**，权威值在 financial_fact.event_time。
"""

from datetime import date, datetime

import duckdb

from src.config import FINANCIAL_DB_PATH


class FinancialIngestLogRepository:

    def __init__(self, db_path: str = FINANCIAL_DB_PATH):
        self.con = duckdb.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_ingest_log
            (
                source VARCHAR NOT NULL,
                code VARCHAR NOT NULL,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                stat_date DATE,
                status VARCHAR NOT NULL,
                saved INTEGER,
                skipped INTEGER,
                failed INTEGER,
                error VARCHAR,
                finished_at TIMESTAMP NOT NULL,

                UNIQUE (source, code, year, quarter)
            )
            """
        )

    def record(
            self,
            source: str,
            code: str,
            year: int,
            quarter: int,
            status: str,
            stat_date: date | None = None,
            saved: int = 0,
            skipped: int = 0,
            failed: int = 0,
            error: str | None = None,
    ) -> None:
        """写一行（同键覆盖）。status 取值：success / empty / failed"""
        self.con.execute(
            """
            INSERT INTO financial_ingest_log
                (source, code, year, quarter, stat_date, status,
                 saved, skipped, failed, error, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (source, code, year, quarter) DO UPDATE SET
                stat_date = EXCLUDED.stat_date,
                status = EXCLUDED.status,
                saved = EXCLUDED.saved,
                skipped = EXCLUDED.skipped,
                failed = EXCLUDED.failed,
                error = EXCLUDED.error,
                finished_at = EXCLUDED.finished_at
            """,
            [source, code, year, quarter, stat_date, status,
             saved, skipped, failed, error, datetime.now()],
        )

    def done_keys(self, source: str) -> set[tuple[str, int, int]]:
        """做完的请求键。**'empty' 也算做完** —— 否则空结果会被永远重试。"""
        rows = self.con.execute(
            """
            SELECT code, year, quarter FROM financial_ingest_log
            WHERE source = ? AND status IN ('success', 'empty')
            """,
            [source],
        ).fetchall()
        return {(row[0], row[1], row[2]) for row in rows}

    def close(self):
        self.con.close()
