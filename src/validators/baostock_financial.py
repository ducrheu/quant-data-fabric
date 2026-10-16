"""Baostock 财务原始行的格式校验（消费 RawRecord）。

只管"能不能被 normalizer 安全消费"，不管业务合理性。
业务校验（如 pubDate 早于 statDate）跟着统一模型走，本轮不做。
"""

from datetime import datetime

from src.domain.raw import RawRecord


def validate_baostock_profit_raw(raw: RawRecord) -> list[str]:
    errors = []
    data = raw.raw_data

    code = data.get("code")
    if not code:
        errors.append("missing code")
    else:
        parts = str(code).split(".")
        if len(parts) != 2 or parts[0] not in ("sz", "sh") or not parts[1].isdigit():
            errors.append("invalid code")

    try:
        float(data["netProfit"])
    except (KeyError, TypeError, ValueError):
        errors.append("invalid netProfit")

    for field in ("statDate", "pubDate"):
        try:
            datetime.strptime(data[field], "%Y-%m-%d")
        except (KeyError, TypeError, ValueError):
            errors.append(f"invalid {field}")

    return errors