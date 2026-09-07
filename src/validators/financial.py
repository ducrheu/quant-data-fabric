from datetime import datetime
from src.domain.raw import RawRecord

def validate_income_raw(raw: RawRecord) -> list[str]:
    errors = []
    data = raw.raw_data

    if not data.get("ts_code"):
        errors.append("missing ts_code")

    try:
        float(data["n_income"])
    except (KeyError, TypeError, ValueError):
        errors.append("invalid n_income")

    end_date = data.get("end_date")
    try:
        datetime.strptime(end_date, "%Y%m%d")
    except (TypeError, ValueError):
        errors.append("invalid end_date")

    ann_date = data.get("ann_date")
    try:
        datetime.strptime(ann_date, "%Y%m%d")
    except (TypeError, ValueError):
        errors.append("invalid ann_date")

    return errors