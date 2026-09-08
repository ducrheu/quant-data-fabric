from datetime import datetime
import pandas as pd

from src.connectors.tushare_connector import TushareConnector
from src.normalizers.financial import TushareFinancialNormalizer
from src.pipelines.financial import FinancialPipeline
from src.repositories.financial import FinancialRepository

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
            "end_date": "20251231",
            "ann_date": "20260615",
        },
    ]

    pipeline, repository = make_pipeline(tmp_path, rows)
    result = pipeline.run("600519.SH", "20250101", "20251231")
    repository.close()

    assert result.total == 3
    assert result.saved == 2
    assert result.failed == 1
    assert len(result.errors) == 1