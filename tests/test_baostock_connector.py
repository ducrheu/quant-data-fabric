import pytest
from src.connectors.baostock_connector import BaostockFinancialConnector

class FakeBaostockResult:
    def __init__(self, rows, error_code="0", error_msg="success"):
        self.fields = ["code", "pubDate", "statDate", "netProfit", "epsTTM"]
        self._rows = [list(row) for row in rows]
        self._index = -1
        self.error_code = error_code
        self.error_msg = error_msg

    def next(self):
        self._index += 1
        return self._index < len(self._rows)

    def get_row_data(self):
        return self._rows[self._index]

class FakeBaostockClient:
    def __init__(self, rows, error_code="0", error_msg='success'):
        self.rows = rows
        self.error_code = error_code
        self.error_msg = error_msg

    def query_profit_data(self, code, year, quarter):
        return FakeBaostockResult(self.rows, self.error_code, self.error_msg)

def test_connector_turns_cursor_rows_into_raw_records():
    client = FakeBaostockClient([
        ["sh.600519", "2025-04-03", "2024-12-31", "89334728025.90", "68.642173"],
    ])
    records = BaostockFinancialConnector(client).fetch_profit("sh.600519", 2024, 4)
    assert len(records) == 1
    assert records[0].source == "baostock"
    assert records[0].raw_data["code"] == "sh.600519"
    assert records[0].raw_data["pubDate"] == "2025-04-03"

def test_connector_returns_empty_list_when_no_rows():
    connector = BaostockFinancialConnector(FakeBaostockClient([]))
    assert connector.fetch_profit("sh.600519", 2024, 4) == []

def test_connector_raises_no_api_error():
    client = FakeBaostockClient([], error_code="10001", error_msg="network broken")
    with pytest.raises(RuntimeError):
        BaostockFinancialConnector(client).fetch_profit("sh.600519", 2024, 4)
