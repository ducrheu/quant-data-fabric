from datetime import datetime
from src.domain.factor import FactorRecord

def test_factor_record_create():
    record = FactorRecord(
        symbol = "600519.SH",
        factor_name = "mom_20d",
        trade_time = datetime(2026, 1, 30),
        value = 0.152,
    )

    assert record.symbol == "600519.SH"
    assert record.factor_name == "mom_20d"
    assert record.value == 0.152