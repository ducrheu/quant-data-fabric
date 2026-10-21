"""每日基础指标的存储层。

身份是 (symbol, trade_time, source)：同一天、同一只票、不同数据源各存各的。
**任何读取都必须显式指定 source**——不指定就会同时读到多套数据。
本层目前没有读方法；将来加 get_* 时，source 必须是必填参数，不要给默认值。
"""

import duckdb

from src.config import PRICE_DB_PATH
from src.domain.daily_basic import DailyBasicRecord

class DailyBasicRepository:

    def __init__(self, db_path: str = PRICE_DB_PATH):
        self.con = duckdb.connect(db_path)
        self._create_table()

    def _create_table(self):
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_basic
            (
            symbol VARCHAR NOT NULL,
            trade_time TIMESTAMP NOT NULL,
            close DOUBLE,
            turnover_rate DOUBLE,
            total_mv DOUBLE,
            circ_mv DOUBLE,
            pe_ttm DOUBLE,
            pb DOUBLE,
            source VARCHAR NOT NULL,
                
            UNIQUE (symbol, trade_time, source)
            )
            """
        )
    def save_many(self, records: list[DailyBasicRecord]) -> int:
        """整批原子写入，返回实际插入行数"""
        if not records:
            return 0

        self.con.execute("BEGIN TRANSACTION")
        try:
            before = self._count()
            self.con.executemany(
                """
                INSERT INTO daily_basic
                    (symbol, trade_time, close, turnover_rate, total_mv, circ_mv, pe_ttm, pb, source)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                """,
                [
                    (
                        r.symbol, r.trade_time, r.close, r.turnover_rate, r.total_mv, r.circ_mv, r.pe_ttm, r.pb, r.source
                    )
                    for r in records
                ],
            )
            after = self._count()
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise

        return after - before

    def _count(self):
        return self.con.execute("SELECT COUNT(*) FROM daily_basic").fetchone()[0]

    def close(self):
        self.con.close()