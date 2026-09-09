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

    def save(self, record: PriceRecord):
        self.con.execute(
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

    def close(self):
        self.con.close()
