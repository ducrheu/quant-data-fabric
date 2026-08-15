from datetime import datetime

from src.domain.raw import RawRecord
from src.normalizers.financial import TushareFinancialNormalizer

def test_tushare_financial_normalizer():

    raw = RawRecord(

        source = "tushare",

        raw_data = {

            "ts_code": "600519.SH",

            "n_income": 80000000000,

            "end_date": "20251231",

            "ann_date": "20260430"

        },

        ingest_time = datetime(2025, 5, 1)

    )

    normalizer = TushareFinancialNormalizer()
    
    record = normalizer.normalize(raw)


    assert record.symbol == "600519.SH"

    assert record.metric_name == "net_income"

    assert record.value == 80000000000

    assert record.available_time == datetime(2026, 4, 30)