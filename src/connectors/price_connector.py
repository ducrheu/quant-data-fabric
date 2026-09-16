from datetime import datetime

from src.domain.raw import RawRecord

class TusharePriceConnector:
    def __init__(self, client):
        self.client = client

    def fetch_daily(self, ts_code, start_date, end_date):
        df = self.client.daily(
            ts_code = ts_code,
            start_date = start_date,
            end_date = end_date,
        )
        return self._to_raw_record(df)

    def fetch_daily_market(self, trade_date):
        df = self.client.daily(trade_date = trade_date)
        return self._to_raw_record(df)

    def _to_raw_record(self, df):
        records = []

        for _, row in df.iterrows():
            record = RawRecord(
                source = "tushare",
                raw_data = row.to_dict(),
                ingest_time = datetime.now(),
            )
            records.append(record)

        return records