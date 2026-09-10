from datetime import datetime

from src.domain.price import PriceRecord
from src.domain.raw import RawRecord

def validate_daily_raw(raw: RawRecord) -> list[str]:
    """Format checks on the raw Tushare daily payload."""
    errors = []
    data = raw.raw_data

    if not data.get("ts_code"):
        errors.append("missing ts_code")

    for field in ("open", "high", "low", "close", "vol"):
        try:
            float(data[field])
        except (KeyError, TypeError, ValueError):
            errors.append(f"invalid {field}")

    trade_date = data.get("trade_date")
    try:
        datetime.strptime(trade_date, "%Y%m%d")
    except (ValueError, TypeError):
        errors.append(f"invalid trade_date")

    return errors

def validate_price_record(record: PriceRecord) -> list[str]:
    """Business checks on the normalized price record."""
    errors = []

    if record.symbol.count(".") != 1:
        errors.append("invalid symbol format")

    for name, value in (
        ("open", record.open),
        ("high", record.high),
        ("low", record.low),
        ("close", record.close),
    ):
        if value <= 0:
            errors.append(f"non-positive {name}")

    if record.high < record.low:
        errors.append("high below low")

    if record.volume < 0:
        errors.append("negative volume")

    return errors
