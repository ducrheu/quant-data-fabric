"""Baostock 财务数据连接器（季频）。

baostock 是游标式 API（fields + next() + get_row_data()），不是 DataFrame，
所以不能照抄 Tushare 那种 df.iterrows()。

只负责"取回来"，不校验、不映射字段——那是 validator 和 normalizer 的活。
client 注入：真实用法传 baostock 模块本身（需已 login），测试传假 client，全程离线。
"""

from datetime import datetime

from src.domain.raw import RawRecord


class BaostockFinancialConnector:
    def __init__(self, client):
        self.client = client

    def fetch_profit(self, code: str, year: int, quarter: int) -> list[RawRecord]:
        result = self.client.query_profit_data(code=code, year=year, quarter=quarter)

        if result.error_code != "0":
            raise RuntimeError(f"baostock error {result.error_code}: {result.error_msg}")

        records = []
        while result.next():
            row = dict(zip(result.fields, result.get_row_data()))
            records.append(
                RawRecord(
                    source="baostock",
                    raw_data=row,
                    ingest_time=datetime.now()
                )
            )
        return records