from datetime import datetime

import duckdb

from src.domain.factor import FactorRecord

class FactorRepository:

    def __init__(self, db_path: str = "data/factor.duckdb"):
        self.con = duckdb.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS factor_daily
            (
                symbol VARCHAR NOT NULL,
                factor_name VARCHAR NOT NULL,
                trade_time TIMESTAMP NOT NULL,
                value DOUBLE NOT NULL,
                
                UNIQUE(symbol, factor_name, trade_time)
            )
            """
        )

    def save(self, record: FactorRecord) -> int:
        result = self.con.execute(
            """
            INSERT INTO factor_daily (symbol, factor_name, trade_time, value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [
                record.symbol,
                record.factor_name,
                record.trade_time,
                record.value,
            ],
        )
        return result.fetchone()[0]

    def get_series(
            self,
            symbol: str,
            factor_name: str,
            start_time: datetime,
            end_time: datetime,
    ) -> list[FactorRecord]:
        rows = self.con.execute(
            """
            SELECT symbol, factor_name, trade_time, value
            FROM factor_daily
                WHERE symbol = ?
                AND factor_name = ?
                AND trade_time >= ?
                AND trade_time <= ?
            Order by trade_time ASC
            """,
            [symbol, factor_name, start_time, end_time],
        ).fetchall()

        return [
            FactorRecord(
                symbol = row[0],
                factor_name = row[1],
                trade_time = row[2],
                value = row[3],
            )
            for row in rows
        ]

    def close(self):
        self.con.close()