"""摄入批次（ingest_batch）：一次 API 调用 = 一条记录，供数据血缘使用。

与 ingest_log 的区别：
- ingest_log   按 (trade_date, source) 记账，回答"哪天做完了"，用于断点恢复
- ingest_batch 按 batch_id 记账，回答"哪一次调用、参数是什么"，用于血缘与重放
"""

from datetime import datetime

import duckdb

from src.config import FINANCIAL_DB_PATH

class IngestBatchRepository:

    def __init__(self, db_path: str = FINANCIAL_DB_PATH):
        self.con = duckdb.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_batch
            (
                batch_id INTEGER NOT NULL,
                source VARCHAR NOT NULL,
                api_name VARCHAR NOT NULL,
                params VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                started_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP,
                total INTEGER,
                saved INTEGER,
                restated INTEGER,
                skipped INTEGER,
                failed INTEGER,
                error VARCHAR,
                
                PRIMARY KEY (batch_id)
            )
            """
        )

    def start(self, source: str, api_name: str, params: str) -> int:
        """开一个批次，返回 batch_id。

        先记 status='running'：若程序此后崩溃，这行会永远停在 running，
        正是"上次有个批次没跑完"的证据。
        """

        batch_id = self.con.execute(
            "SELECT COALESCE (MAX(batch_id), 0) + 1 FROM ingest_batch"
        ).fetchone()[0]

        self.con.execute(
            """
            INSERT INTO ingest_batch
                (batch_id, source, api_name, params, status, started_at)
            VALUES (?, ?, ?, ?, 'running', ?)
            """,
            [batch_id, source, api_name, params, datetime.now()],
        )
        return batch_id

    def finish(
            self,
            batch_id: int,
            status: str,
            total: int,
            saved: int,
            restated: int,
            skipped: int,
            failed: int,
            error: str | None = None,
    ) -> None:
        """收口一个批次：写入状态、计数与结束时间"""
        self.con.execute(
            """
            UPDATE ingest_batch
            SET status = ?,
                finished_at = ?,
                total = ?,
                saved = ?,
                restated = ?,
                skipped = ?,
                failed = ?,
                error = ?,
            WHERE batch_id = ?
            """,
            [status, datetime.now(), total, saved, restated, skipped, failed, error, batch_id],
        )

    def get(self, batch_id: int):
        """按 batch_id 取回批次——血缘查询的入口（这次调用的参数）"""
        return self.con.execute(
            """
            SELECT batch_id, source, api_name, params, status, started_at, finished_at, total, saved, restated, skipped, failed, error
            FROM ingest_batch
                WHERE batch_id = ?
            """,
            [batch_id],
        ).fetchone()

    def close(self):
        self.con.close()