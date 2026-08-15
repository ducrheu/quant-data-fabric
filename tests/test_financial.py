from datetime import datetime
from src.domain.financial import FinancialRecord

def test_financial_record_create():

    record = FinancialRecord(

        symbol = "600519.SH",

        metric_name = "roe",

        value =  0.25,

        event_time = datetime(2025, 12, 31),

        available_time = datetime(2025, 4, 30),

        processing_time = datetime(2025, 5, 1),

        source = "tushare"

    )

    assert record.symbol == "600519.SH"

    assert record.value == 0.25