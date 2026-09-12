from datetime import datetime
import duckdb
from src.domain.price import PriceRecord

class PriceRepository:
    def __init__(self, db_path: str = "data/price.duckdb"):
        self.con = duckdb.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.con.execute("""
        CREATE TABLE IF NOT EXISTS price_daily
        (
        symbol VARCHAR NOT NULL,
        trade_time TIMESTAMP NOT NULL,
        open DOUBLE NOT NULL,
        high DOUBLE NOT NULL,
        low DOUBLE NOT NULL,
        close DOUBLE NOT NULL,
        volume DOUBLE NOT NULL,
        source VARCHAR NOT NULL,
            
        UNIQUE (symbol, trade_time)
        )
        """
    )

    def save(self, record: PriceRecord) -> int:
        result = self.con.execute(
            """
            INSERT INTO price_daily
                (symbol, trade_time, open, high, low, close, volume, source)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [
                record.symbol,
                record.trade_time,
                record.open,
                record.high,
                record.low,
                record.close,
                record.volume,
                record.source
            ],
        )
        return result.fetchone()[0]

    def get_range(
            self,
            symbol: str,
            start_time: datetime,
            end_time: datetime,
    ) -> list[PriceRecord]:
        rows = self.con.execute(
            """
            SELECT symbol, trade_time, open, high, low, close, volume, source
            FROM price_daily
                WHERE symbol = ?
                AND trade_time >= ?
                AND trade_time <= ?
            ORDER BY trade_time ASC
            """,
            (symbol, start_time, end_time)
        ).fetchall()

        return [
            PriceRecord(
                symbol = row[0],
                trade_time = row[1],
                open = row[2],
                high = row[3],
                low = row[4],
                close = row[5],
                volume = row[6],
                source = row[7],
            )
            for row in rows
        ]

    def close(self):
        self.con.close()
