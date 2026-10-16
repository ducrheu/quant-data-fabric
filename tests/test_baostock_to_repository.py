from datetime import datetime

import pytest

from src.connectors.baostock_connector import BaostockFinancialConnector
from src.domain.financial import FinancialRecord, SaveOutcome
from src.normalizers.baostock_financial import BaostockFinancialNormalizer
from src.repositories.financial import FinancialRepository

class FakeBaostockResult:
    """复刻 baostock 的游标协议：fields + next() + get_row_data()"""
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
    def __init__(self, rows, error_code="0", error_msg="success"):
        self.rows = rows
        self.error_code = error_code
        self.error_msg = error_msg

    def query_profit_data(self, code, year, quarter):
        return FakeBaostockResult(self.rows, self.error_code, self.error_msg)

@pytest.fixture
def repository(tmp_path):
    repo = FinancialRepository(str(tmp_path / "financial.duckdb"))
    yield repo
    repo.close()

def _ingest_maotai(repository):
    client = FakeBaostockClient([
        ["sh.600519", "2025-04-03", "2024-12-31", "89334728025.90", "68.642173"]
    ])
    raw = BaostockFinancialConnector(client).fetch_profit("sh.600519", 2024, 4)[0]
    return BaostockFinancialNormalizer().normalize(raw)

def test_pit_gate_hides_row_before_disclosure(repository):
    repository.save(_ingest_maotai(repository))

    before = repository.get_pit("600519.SH", "net_income", "baostock", datetime(2025, 4, 2))
    after = repository.get_pit("600519.SH", "net_income", "baostock", datetime(2025, 4, 3))

    assert before is None
    assert after is not None
    assert after[2] == 89334728025.90

def test_second_run_is_idempotent(repository):
    record = _ingest_maotai(repository)

    assert repository.save(record) == SaveOutcome.INSERTED
    assert repository.save(record) == SaveOutcome.DUPLICATE

    count = repository.con.execute("SELECT COUNT(*) FROM financial_fact").fetchone()[0]
    assert count == 1

def test_baostock_and_tushare_do_not_overwrite_each_other(repository):
    """同报告期、同指标、不同源：各存各的，不互相覆盖"""
    from_baostock = _ingest_maotai(repository)
    from_tushare = FinancialRecord(
        symbol="600519.SH",
        metric_name="net_income",
        value=89334728025.90,
        event_time=datetime(2024, 12, 31),
        available_time=datetime(2025, 4, 3),
        processing_time=datetime(2026, 10, 12),
        source="tushare",
    )

    assert repository.save(from_baostock) == SaveOutcome.INSERTED
    assert repository.save(from_tushare) == SaveOutcome.INSERTED

    rows = repository.con.execute(
        "SELECT source, revision_id FROM financial_fact ORDER BY source"
    ).fetchall()
    assert rows == [("baostock", 1), ("tushare", 1)]