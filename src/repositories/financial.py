from datetime import datetime
import duckdb
from src.domain.financial import FinancialRecord


class FinancialRepository:

    def __init__(self, db_path: str = "data/quant_data.duckdb"):
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

    def save(self, record: FinancialRecord) -> int:
        result = self.con.execute(
            """
            INSERT INTO financial_fact(symbol,
                                       metric_name,
                                       value,
                                       event_time,
                                       available_time,
                                       processing_time,
                                       source,
                                       revision_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING
            """,
            [
                record.symbol,
                record.metric_name,
                record.value,
                record.event_time,
                record.available_time,
                record.processing_time,
                record.source,
                record.revision_id,
            ],
        )
        return result.fetchone()[0]

    def get_pit(
            self,
            symbol: str,
            metric_name: str,
            as_of_time: datetime,
            event_time: datetime | None = None,
    ):
        if event_time is None:
            order_clause = "ORDER BY event_time DESC, available_time DESC"
            event_filter = ""
            params = [symbol, metric_name, as_of_time]
        else:
            order_clause = "ORDER BY available_time DESC"
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

