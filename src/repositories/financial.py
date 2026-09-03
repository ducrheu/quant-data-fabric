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

    def save(self, record: FinancialRecord):
        self.con.execute(
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

    def get_pit(
            self,
            symbol: str,
            metric_name: str,
            as_of_time: datetime,
    ):
        return self.con.execute(
            """
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
              AND available_time <= ?
            ORDER BY event_time DESC LIMIT 1
            """,
            [
                symbol,
                metric_name,
                as_of_time,
            ],
        ).fetchone()

    def close(self):
        self.con.close()

