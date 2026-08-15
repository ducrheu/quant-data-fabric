import csv
from pathlib import Path
from datetime import datetime
from src.domain.raw import RawRecord

class CSVConnector:

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def fetch(self):

        records = []

        with open(
            self.file_path,
            "r",
            encoding="utf-8"
        )as f:
            reader = csv.DictReader(f)

            for row in reader:
                record = RawRecord(
                    source = "csv",
                    raw_data = row,
                    ingest_time = datetime.now()
                )

                records.append(record)

        return records
