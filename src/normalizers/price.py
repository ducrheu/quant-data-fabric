from datetime import datetime

from src.domain.price import PriceRecord
from src.domain.raw import RawRecord
from src.normalizers.base import BaseNormalizer

class TusharePriceNormalizer(BaseNormalizer):
    def normalize(self, raw: RawRecord) -> PriceRecord:
        data = raw.raw_data

        record = PriceRecord(
            symbol = data["ts_code"],
            trade_time = datetime.strptime(data["trade_date"], "%Y%m%d"),
            open = float(data["open"]),
            high = float(data["high"]),
            low = float(data["low"]),
            close = float(data["close"]),
            volume = float(data["vol"]),
            source = raw.source,
        )

        return record