from datetime import datetime

from src.domain.raw import RawRecord
from src.normalizers.baostock_daily_basic import BaostockDailyBasicNormalizer

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
    return RawRecord(source="baostock", raw_data=data, ingest_time = datetime(2026, 10, 21))

def test_maps_baostock_row():
    record = BaostockDailyBasicNormalizer().normalize(make_raw())

    assert record.symbol == "600519.SH"
    assert record.trade_time == datetime(2025, 4, 1)
    assert record.close == 1556.02
    assert record.turnover_rate == 0.1477
    assert record.pe_ttm == 23.639829
    assert record.pb == 8.222933
    assert record.source == "baostock"

def test_missing_optional_fields_become_none():
    record = BaostockDailyBasicNormalizer().normalize(make_raw(turn="", peTTM="", pbMRQ=""))

    assert record.turnover_rate is None
    assert record.pe_ttm is None
    assert record.pb is None

def test_market_caps_are_left_empty():
    """baostock 的 k 线不提供总市值/流通市值——不猜，留 None"""
    record = BaostockDailyBasicNormalizer().normalize(make_raw())

    assert record.total_mv is None
    assert record.circ_mv is None