from datetime import datetime

from src.domain.price import PriceRecord
from src.domain.raw import RawRecord
from src.normalizers.base import BaseNormalizer

def _optional_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

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
            amount = _optional_float(data.get("amount")),
            pct_chg = _optional_float(data.get("pct_chg")),
        )

        return record