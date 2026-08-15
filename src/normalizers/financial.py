from datetime import datetime

from src.domain.financial import FinancialRecord
from src.normalizers.base import BaseNormalizer

class TushareFinancialNormalizer(BaseNormalizer):

    def normalize(self, raw):

        data = raw.raw_data
        record =FinancialRecord(

            symbol = data['ts_code'],

            metric_name = "net_income",

            value = float(data["n_income"]),
            
            event_time = datetime.strptime(
                data["end_date"],
                "%Y%m%d"
            ),

            available_time = datetime.strptime(
                data["ann_date"],
                "%Y%m%d"
            ),

            processing_time = raw.ingest_time,
            source = raw.source

        )

        return record
