from datetime import datetime

from src.domain.raw import RawRecord
from src.validators.baostock_daily_basic import validate_baostock_daily_basic_raw

def make_raw(**overrides):
    data = {
        "date": "2025-04-01",
        "code": "sh.600519",
        "close": "1556.0200",
        "turn": "0.147700",
        "tradestatus": "1",
        "peTTM": "23.639829",
        "pbMRQ": "8.222933",
    }
    data.update(overrides)
    return RawRecord(source="baostock", raw_data=data, ingest_time=datetime(2026, 10, 21))


def test_good_row_has_no_errors():
    assert validate_baostock_daily_basic_raw(make_raw()) == []

def test_collects_all_errors_at_once():
    errors = validate_baostock_daily_basic_raw(make_raw(code="600519.SH", date="2025/04/01", close="abc"))

    assert "invalid code" in errors
    assert "invalid date" in errors
    assert "invalid close" in errors

def test_missing_code_is_reported():
    assert "missing code" in validate_baostock_daily_basic_raw(make_raw(code=None))

def test_empty_optional_fields_are_allowed():
    assert validate_baostock_daily_basic_raw(make_raw(turn="", peTTM="", pbMRQ="")) == []