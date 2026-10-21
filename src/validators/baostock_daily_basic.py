"""Baostock 日频估值原始行的格式校验（消费 RawRecord）。

只管「能不能被 normalizer 安全消费」。
`turn / peTTM / pbMRQ` 允许为空（baostock 会给 ""），`close` 不允许。
"""

from datetime import datetime

from src.domain.raw import RawRecord

def validate_baostock_daily_basic_raw(raw: RawRecord) -> list[str]:
    errors = []
    data = raw.raw_data

    code = data.get("code")
    if not code:
        errors.append("missing code")
    else:
        parts = str(code).split(".")
        if len(parts) != 2 or parts[0] not in ("sh", "sz") or not parts[1].isdigit():
            errors.append("invalid code")

    try:
        datetime.strptime(data["date"], "%Y-%m-%d")
    except (KeyError, TypeError, ValueError):
        errors.append("invalid date")

    try:
        float(data["close"])
    except(KeyError, TypeError, ValueError):
        errors.append("invalid close")

    return errors