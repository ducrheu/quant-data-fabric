from datetime import datetime

import pytest

from src.domain.raw import RawRecord
from src.normalizers.baostock_financial import BaostockFinancialNormalizer, to_ts_code

def test_symbol_mapping_covers_both_makers():
    assert to_ts_code("sh.600519") == "600519.SH"
    assert to_ts_code("sz.000024") == "000024.SZ"

def test_normalizer_maps_baostock_row():
    raw = RawRecord(
        source="baostock",
        raw_data={
            "code": "sh.600519",
            "pubDate": "2025-04-03",
            "statDate": "2024-12-31",
            "netProfit": "89334728025.90",
        },
        ingest_time=datetime(2026, 10, 12),
    )
    record = BaostockFinancialNormalizer().normalize(raw)

    assert record.symbol == "600519.SH"
    assert record.metric_name == "net_income"
    assert record.value == 89334728025.90
    assert record.event_time == datetime(2024, 12, 31)
    assert record.available_time == datetime(2025, 4, 3)
    assert record.source == "baostock"

def test_normalizer_rejects_compact_date():
    """baostock 是 YYYY-MM-DD。喂 YYYYMMDD 必须炸，不能静默错"""
    raw = RawRecord(
        source="baostock",
        raw_data={
            "code": "sh.600519",
            "pubDate": "20250403",
            "statDate": "20241231",
            "netProfit": "1",
        },
        ingest_time=datetime(2026, 10, 12)
    )

    with pytest.raises(ValueError):
        BaostockFinancialNormalizer().normalize(raw)