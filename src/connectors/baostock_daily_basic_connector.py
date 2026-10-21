"""Baostock 日频估值/流动性数据连接器。

baostock 的 query_history_k_data_plus 按「证券 × 区间」返回，一次拿一只票的一段日线；
和 Tushare 的 daily_basic 按「交易日拉全市场」正好相反。

字段口径（2026-10-21 实测）：
- close       收盘价（不复权，adjustflag=3）
- turn        换手率，**百分比**（0.1477 表示 0.1477%）
- peTTM       市盈率（TTM）
- pbMRQ       市净率（MRQ）
- tradestatus 1=正常交易，0=停牌

本源不提供 total_mv / circ_mv，这两列留空——不猜、不用别的字段凑。
"""

from datetime import datetime

from src.domain.raw import RawRecord

class BaostockDailyBasicConnector:
    FIELDS = "date,code,close,turn,tradestatus,peTTM,pbMRQ"

    def __init__(self, client):
        self.client = client

    def fetch_daily_basic(self, code: str, start_date: str, end_date: str) -> list[RawRecord]:
        result = self.client.query_history_k_data_plus(
            code,
            self.FIELDS,
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3",
        )

        if result.error_code != "0":
            raise RuntimeError(f"baostock error {result.error_code}: {result.error_msg}")

        records = []
        while result.next():
            row = dict(zip(result.fields, result.get_row_data()))

            # 停牌日没有有意义的估值；跳过，别写成一行空数据
            if row.get("tradestatus") != "1":
                continue

            records.append(
                RawRecord(
                    source="baostock",
                    raw_data=row,
                    ingest_time=datetime.now()
                )
            )
        return records
