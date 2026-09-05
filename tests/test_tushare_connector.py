import pandas as pd
from src.connectors.tushare_connector import TushareConnector
from src.normalizers.financial import TushareFinancialNormalizer
from datetime import datetime

class MockTushareClient:
    def income(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": "600519.SH",
                    "n_income": 80000000000,
                    "end_date": "20251231",
                    "ann_date": "20260430",
                }
            ]
        )

def test_tushare_connector_returns_raw_records():
    client = MockTushareClient()
    connector = TushareConnector(client)

    records = connector.fetch_income(
        ts_code = "600519.SH",
        start_date = "20250101",
        end_date = "20251231",
    )

    assert len(records) == 1
    assert records[0].source == "tushare"
    assert records[0].raw_data["ts_code"] == "600519.SH"
    assert records[0].raw_data["n_income"] == 80000000000

def test_tushare_connector_output_can_be_normalized():
    client = MockTushareClient()
    connector = TushareConnector(client)
    normalizer = TushareFinancialNormalizer()
    raw_records = connector.fetch_income(
        ts_code = "600519.SH",
        start_date = "20250101",
        end_date = "20251231",
    )
    record = normalizer.normalize(raw_records[0])
    assert record.symbol == "600519.SH"
    assert record.metric_name == "net_income"
    assert record.value ==80000000000
    assert record.event_time == datetime(2025, 12, 31)
    assert record.available_time == datetime(2026, 4, 30)
    assert record.source == "tushare"