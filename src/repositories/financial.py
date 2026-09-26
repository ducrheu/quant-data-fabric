from datetime import datetime
import duckdb
from src.domain.financial import FinancialRecord, SaveOutcome
from src.config import FINANCIAL_DB_PATH


class FinancialRepository:

    def __init__(self, db_path: str = FINANCIAL_DB_PATH):
        self.con = duckdb.connect(db_path)

        self._create_table()

    def _create_table(self):
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_fact
            (
                symbol
                VARCHAR
                NOT
                NULL,
                metric_name
                VARCHAR
                NOT
                NULL,
                value
                DOUBLE
                NOT
                NULL,
                event_time
                TIMESTAMP
                NOT
                NULL,
                available_time
                TIMESTAMP
                NOT
                NULL,
                processing_time
                TIMESTAMP
                NOT
                NULL,
                source
                VARCHAR
                NOT
                NULL,
                revision_id
                INTEGER
                NOT
                NULL,

                UNIQUE
            (
                symbol,
                metric_name,
                event_time,
                revision_id
            )
                )
            """
        )

    def save(self, record: FinancialRecord) -> SaveOutcome:
        # 1. 查出同一事实(symbol + metric + event_time) 已有的所有版本
        existing = self.con.execute(
            """
            SELECT revision_id, available_time, value
            FROM financial_fact
            WHERE symbol = ? AND metric_name = ? AND event_time = ?
            ORDER BY revision_id    
            """,
            [record.symbol, record.metric_name, record.event_time],
        ).fetchall()

        # 2. 有一条 available_time 和 value 都相同 -> 真幂等重跑
        for _, available_time, value in existing:
            if available_time == record.available_time and value == record.value:
                return SaveOutcome.DUPLICATE

        # 3. 决定 revision_id: 有历史就 +1 没有就是第一版
        if existing:
            revision_id = max(row[0] for row in existing) + 1
            outcome = SaveOutcome.RESTATED
        else:
            revision_id = 1
            outcome = SaveOutcome.INSERTED

        # 4. 插入 (revision_id 有这里算出，不用再用 record.revision_id)
        self.con.execute(
            """
            INSERT INTO financial_fact(
            symbol,
            metric_name,
            value,
            event_time,
            available_time,
            processing_time,
            source,
            revision_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [record.symbol, record.metric_name, record.value, record.event_time, record.available_time, record.processing_time, record.source, revision_id,],
        )
        return outcome

    def get_pit(
            self,
            symbol: str,
            metric_name: str,
            as_of_time: datetime,
            event_time: datetime | None = None,
    ):
        if event_time is None:
            order_clause = "ORDER BY event_time DESC, available_time DESC, revision_id DESC"
            event_filter = ""
            params = [symbol, metric_name, as_of_time]
        else:
            order_clause = "ORDER BY available_time DESC, revision_id DESC"
            event_filter = "AND event_time = ?"
            params = [symbol, metric_name, event_time, as_of_time]

        return self.con.execute(
            f"""
            SELECT symbol,
                   metric_name,
                   value,
                   event_time,
                   available_time,
                   processing_time,
                   source,
                   revision_id
            FROM financial_fact
            WHERE symbol = ?
              AND metric_name = ?
                {event_filter}
              AND available_time <= ?
            {order_clause}
            LIMIT 1
            """,
            params,
        ).fetchone()

    def close(self):
        self.con.close()

