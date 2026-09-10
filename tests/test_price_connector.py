from datetime import datetime

import pandas as pd

from src.connectors.price_connector import TusharePriceConnector
from src.normalizers.price import TusharePriceNormalizer

class FakeTushareClient:
    def daily(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": "600519.SH",
                    "trade_date": "20260109",
                    "open": 1417.0,
                    "high": 1428.6,
                    "low": 1416.01,
                    "close": 1419.1,
                    "pre_close": 1412.3,
                    "change": 6.8,
                    "pct_chg": 0.4815,
                    "vol": 29847.74,
                    "amount": 4243865.418,
                }
            ]
        )

def test_price_connector_returns_raw_records():
    client = FakeTushareClient()
    connector = TusharePriceConnector(client)
    records = connector.fetch_daily(
        ts_code="600519.SH",
        start_date="20260101",
        end_date="20260110",
    )
    assert len(records) == 1
    assert records[0].source == "tushare"
    assert records[0].raw_data["ts_code"] == "600519.SH"
    assert records[0].raw_data["trade_date"] == "20260109"

def test_price_connector_output_can_be_normalized():
    client = FakeTushareClient()
    connector = TusharePriceConnector(client)
    normalizer = TusharePriceNormalizer()

    raw_records = connector.fetch_daily(
        ts_code="600519.SH",
        start_date="20260101",
        end_date="20260110",
    )

    record = normalizer.normalize(raw_records[0])

    assert record.symbol == "600519.SH"
    assert record.trade_time == datetime(2026, 1, 9)
    assert record.close == 1419.1
    assert record.volume == 29847.74
    assert record.source == "tushare"