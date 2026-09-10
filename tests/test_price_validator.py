from datetime import datetime

from src.domain.price import PriceRecord
from src.domain.raw import RawRecord
from src.validators.price import validate_daily_raw, validate_price_record

def test_format_validator_passes_good_raw():
    # Arrange
    raw = RawRecord(
        source="tushare",
        raw_data={
            "ts_code": "600519.SH",
            "trade_date": "20260109",
            "open": 1417.0,
            "high": 1428.6,
            "low": 1416.01,
            "close": 1419.1,
            "vol": 29847.74,
        },
        ingest_time = datetime(2026, 1, 10),
    )

    # ACT
    errors = validate_daily_raw(raw)

    # Assert
    assert errors == []

def test_format_validator_catches_bad_fields():
    raw = RawRecord(
        source = "tushare",
        raw_data = {
            # ts_code 故意缺失
            "open": "abc",
            "high": 1428.6,
            "low": 1416.01,
            "close": 1419.1,
            "vol": 29847.74,
        },
        ingest_time = datetime(2026, 1, 10),
    )
    errors = validate_daily_raw(raw)

    assert "missing ts_code" in errors
    assert "invalid open" in errors
    assert "invalid trade_date" in errors

def test_business_validator_passes_good_record():
    record = PriceRecord(
        symbol="600519.SH",
        trade_time=datetime(2026, 1, 9),
        open=1417.0,
        high=1428.6,
        low=1416.01,
        close=1419.1,
        volume=29847.74,
        source="tushare",
    )
    errors = validate_price_record(record)

    assert errors == []

def test_business_validator_catches_high_below_low():
    record = PriceRecord(
        symbol="600519.SH",
        trade_time=datetime(2026, 1, 9),
        open=1417.0,
        high=1400.0,  # 故意让 high < low
        low=1450.0,
        close=1419.1,
        volume=29847.74,
        source="tushare",
    )
    errors = validate_price_record(record)

    assert "high below low" in errors

def test_business_validator_allows_flat_price_day():
    record = PriceRecord(
        symbol="600519.SH",
        trade_time=datetime(2026, 1, 9),
        open=1500.0,
        high=1500.0,  # 一字板：四个价格相同
        low=1500.0,
        close=1500.0,
        volume=100.0,
        source="tushare",
    )

    errors = validate_price_record(record)

    assert errors == []
