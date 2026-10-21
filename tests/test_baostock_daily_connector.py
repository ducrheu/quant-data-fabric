import pytest

from src.connectors.baostock_daily_basic_connector import BaostockDailyBasicConnector


class FakeBaostockResult:
    def __init__(self, rows, error_code="0", error_msg="success"):
        self.fields = ["date", "code", "close", "turn", "tradestatus", "peTTM", "pbMRQ"]
        self.data = [list(row) for row in rows]
        self.cur_row_num = 0
        self.error_code = error_code
        self.error_msg = error_msg

    def next(self):
        return self.cur_row_num < len(self.data)

    def get_row_data(self):
        row = self.data[self.cur_row_num]
        self.cur_row_num += 1
        return row

class FakeBaostockClient:
    def __init__(self, rows, error_code="0", error_msg="success"):
        self.rows = rows
        self.error_code = error_code
        self.error_msg = error_msg
        self.called = None

    def query_history_k_data_plus(self, code, fields, start_date, end_date, frequency, adjustflag):
        self.called = (code, fields, start_date, end_date, frequency, adjustflag)
        return FakeBaostockResult(self.rows, self.error_code, self.error_msg)

def test_fetch_turns_rows_into_raw_records():
    client = FakeBaostockClient([
        ["2025-04-01", "sh.600519", "1556.0200", "0.147700", "1", "23.639829", "8.222933"],
    ])
    records = BaostockDailyBasicConnector(client).fetch_daily_basic("sh.600519", "2025-04-01", "2025-04-04")

    assert len(records) == 1
    assert records[0].source == "baostock"
    assert records[0].raw_data["close"] == "1556.0200"

def test_fetch_uses_unadjusted_prices():
    client = FakeBaostockClient([])
    BaostockDailyBasicConnector(client).fetch_daily_basic("sh.600519", "2025-04-01", "2025-04-04")

    assert client.called[-1] =="3"

def test_fetch_skips_suspended_days():
    client = FakeBaostockClient([
        ["2025-04-01", "sh.600519", "1556.0200", "0.1477", "1", "23.6", "8.2"],
        ["2025-04-02", "sh.600519", "", "", "0", "", ""],
    ])
    records = BaostockDailyBasicConnector(client).fetch_daily_basic("sh.600519", "2025-04-01", "2025-04-04")

    assert len(records) == 1

def test_fetch_raises_on_api_error():
    client = FakeBaostockClient([], error_code="10001", error_msg="network broken")

    with pytest.raises(RuntimeError):
        BaostockDailyBasicConnector(client).fetch_daily_basic("sh.600519", "2025-04-01", "2025-04-04")