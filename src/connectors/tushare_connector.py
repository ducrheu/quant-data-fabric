from src.domain.raw import RawRecord
from datetime import datetime



class TushareConnector:
    def __init__(self, client):
        self.client = client

    def fetch_income(self, ts_code: str, start_date: str, end_date: str):
        df = self.client.income(
            ts_code = ts_code,
            start_date = start_date,
            end_date=end_date
        )

        records = []

        for _, row in df.iterrows():
            record = RawRecord(
                source = "tushare",
                raw_data=row.to_dict(),
                ingest_time=datetime.now(),
            )
            records.append(record)

        return records