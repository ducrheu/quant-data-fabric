from datetime import datetime
import pandas as pd

from src.domain.financial import FinancialRecord
from src.connectors.tushare_connector import TushareConnector
from src.normalizers.financial import TushareFinancialNormalizer
from src.pipelines.financial import FinancialPipeline
from src.repositories.financial import FinancialRepository
from src.repositories.ingest_batch import IngestBatchRepository

class FakeTushareClient:
    def __init__(self, rows):
        self.rows = rows

    def income(self, ts_code, start_date, end_date):
        return pd.DataFrame(self.rows)


def make_pipeline(tmp_path, rows):
    client = FakeTushareClient(rows)
    connector = TushareConnector(client)
    normalizer = TushareFinancialNormalizer()
    repository = FinancialRepository(str(tmp_path / "test.duckdb"))
    pipeline = FinancialPipeline(connector, normalizer, repository)
    return pipeline, repository

def test_pipeline_saves_good_rows_and_skips_bad(tmp_path):
    rows = [
        {
            "ts_code": "600519.SH",
            "n_income": 80000000000,
            "end_date": "20251231",
            "ann_date": "20260430",
        },
        {
            "ts_code": "600519.SH",
            "n_income": "abc",  # 坏数据
            "end_date": "20251231",
            "ann_date": "20260430",
        },
        {
            "ts_code": "600519.SH",
            "n_income": 78000000000,
            "end_date": "20260331",
            "ann_date": "20260615",
        },
    ]

    pipeline, repository = make_pipeline(tmp_path, rows)
    result = pipeline.run(ts_code="600519.SH", start_date="20250101", end_date="20251231")
    repository.close()

    assert result.total == 3
    assert result.saved == 2
    assert result.skipped == 0
    assert result.failed == 1
    assert len(result.errors) == 1

def test_pipeline_second_run_skips_duplicates(tmp_path):
    rows = [
        {
            "ts_code": "600519.SH",
            "n_income": 80000000000,
            "end_date": "20251231",
            "ann_date": "20260430",
        },
    ]

    pipeline, repository = make_pipeline(tmp_path, rows)

    first = pipeline.run(ts_code="600519.SH", start_date="20250101", end_date="20251231")
    second = pipeline.run(ts_code="600519.SH", start_date="20250101", end_date="20251231")

    rows_in_db = repository.con.execute(
        "SELECT COUNT(*) FROM financial_fact"
    ).fetchone()[0]

    repository.close()

    assert first.saved == 1
    assert second.saved == 0
    assert second.skipped == 1
    assert rows_in_db == 1

def test_pipeline_links_facts_to_batch(tmp_path):
    rows = [
        {
            "ts_code": "600519.SH",
            "n_income": 80000000000,
            "end_date": "20251231",
            "ann_date": "20260430",
        },
    ]

    db_path = str(tmp_path / "test.duckdb")
    client = FakeTushareClient(rows)
    connector = TushareConnector(client)
    normalizer = TushareFinancialNormalizer()
    repository = FinancialRepository(db_path)
    batch_repository = IngestBatchRepository(db_path)
    pipeline = FinancialPipeline(
        connector, normalizer, repository, batch_repository,
    )

    result = pipeline.run(ts_code="600519.SH", start_date="20250101", end_date="20251231")

    batch = batch_repository.get(result.batch_id)
    stored = repository.con.execute(
        "SELECT batch_id FROM financial_fact"
    ).fetchall()

    repository.close()
    batch_repository.close()

    assert result.batch_id == 1
    assert batch[4] == "success"
    assert batch[7] == 1
    assert stored == [(1,)]

def test_pipeline_mark_batch_partial_when_a_row_fails(tmp_path):
    rows = [
        {
            "ts_code": "600519.SH",
            "n_income": 80000000000,
            "end_date": "20251231",
            "ann_date": "20260430",
        },
        {
            "ts_code": "600519.SH",
            "n_income": "abc",  # 坏数据
            "end_date": "20251231",
            "ann_date": "20260430",
        },
    ]
    db_path = str(tmp_path / "test.duckdb")
    client = FakeTushareClient(rows)
    repository = FinancialRepository(db_path)
    batch_repository = IngestBatchRepository(db_path)
    pipeline = FinancialPipeline(
        TushareConnector(client),
        TushareFinancialNormalizer(),
        repository,
        batch_repository,
    )
    result = pipeline.run(ts_code="600519.SH", start_date="20250101", end_date="20251231")
    batch = batch_repository.get(result.batch_id)
    repository.close()
    batch_repository.close()
    assert batch[4] == "partial"
    assert batch[12] is None


def test_pipeline_accepts_injected_validator(tmp_path):
    """校验规则可换：注入一个"一律拒绝"的 validator，好行也应被拦下"""
    rows = [
        {
            "ts_code": "600519.SH",
            "n_income": 80000000000,
            "end_date": "20251231",
            "ann_date": "20260430",
        },
    ]
    repository = FinancialRepository(str(tmp_path / "test.duckdb"))
    pipeline = FinancialPipeline(
        TushareConnector(FakeTushareClient(rows)),
        TushareFinancialNormalizer(),
        repository,
        validator=lambda raw: ["always rejected"],
    )

    result = pipeline.run(ts_code="600519.SH", start_date="20250101", end_date="20251231")
    repository.close()

    assert result.total == 1
    assert result.saved == 0
    assert result.failed == 1
    assert result.errors == ["row 0: ['always rejected']"]


class FakeBaostockResult:
    """复刻 baostock 的游标协议：next() 只看，get_row_data() 才前进"""
    def __init__(self, rows, error_code="0", error_msg="success"):
        self.fields = ["code", "pubDate", "statDate", "netProfit", "epsTTM"]
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

    def query_profit_data(self, code, year, quarter):
        return FakeBaostockResult(self.rows, self.error_code, self.error_msg)


def test_pipeline_runs_baostock_source_end_to_end(tmp_path):
    """同一条流水线跑第二个源：证明它不再绑死 Tushare"""
    from src.connectors.baostock_connector import BaostockFinancialConnector
    from src.normalizers.baostock_financial import BaostockFinancialNormalizer
    from src.validators.baostock_financial import validate_baostock_profit_raw

    client = FakeBaostockClient([
        ["sh.600519", "2025-04-03", "2024-12-31", "89334728025.90", "68.642173"],
    ])
    repository = FinancialRepository(str(tmp_path / "test.duckdb"))
    pipeline = FinancialPipeline(
        BaostockFinancialConnector(client),
        BaostockFinancialNormalizer(),
        repository,
        validator=validate_baostock_profit_raw,
        source="baostock",
        api_name="profit",
    )

    result = pipeline.run(code="sh.600519", year=2024, quarter=4)
    stored = repository.get_pit(
        "600519.SH", "net_income", "baostock", datetime(2025, 4, 3)
    )
    repository.close()

    assert result.total == 1
    assert result.saved == 1
    assert stored[2] == 89334728025.90
