from datetime import datetime

from src.domain.raw import RawRecord
from src.validators.baostock_financial import validate_baostock_profit_raw


def make_raw(**overrides):
    data={
        "code": "sh.600519",
        "pubDate": "2025-04-03",
        "statDate": "2024-12-31",
        "netProfit": "89334728025.90",
    }
    data.update(overrides)
    return RawRecord(source="baostock_financial", raw_data=data, ingest_time=datetime(2026, 10, 12))

def test_collects_all_errors_at_once():
    raw = make_raw(code="600519.SH", pubDate="2025/04/03", statDate="", netProfit="abc")
    errors = validate_baostock_profit_raw(raw)

    assert "invalid code" in errors
    assert "invalid netProfit" in errors
    assert "invalid statDate" in errors
    assert "invalid pubDate" in errors

def test_missing_code_is_reported():
    assert "missing code" in validate_baostock_profit_raw(make_raw(code=None))