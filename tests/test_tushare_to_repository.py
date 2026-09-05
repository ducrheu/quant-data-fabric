from datetime import datetime
import pandas as pd
import pytest

from src.connectors.tushare_connector import TushareConnector
from src.normalizers.financial import TushareFinancialNormalizer
from src.repositories.financial import FinancialRepository

class FakeTushareClient:
    def income (self, ts_code, start_date, end_date):
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

@pytest.fixture
def repository(tmp_path):
    db_path = tmp_path / "financial.duckdb"
    repo = FinancialRepository(str(db_path))

    yield repo

    repo.close()

def test_tushare_data_can_be_saved_and_required(repository):
    client = FakeTushareClient()
    connector = TushareConnector(client)
    normalizer = TushareFinancialNormalizer()

    raw_records = connector.fetch_income(
        ts_code = "600519.SH",
        start_date = "20250101",
        end_date = "20251231",
    )

    financial_record = normalizer.normalize(raw_records[0])

    repository.save(financial_record)

    result = repository.get_pit(
        symbol = "600519.SH",
        metric_name = "net_income",
        as_of_time = datetime(2026, 5, 10)
    )

    assert result is not None
    assert result[0] == "600519.SH"
    assert result[1] == "net_income"
    assert result[2] == 80000000000
    assert result[3] == datetime(2025, 12, 31)
    assert result[4] == datetime(2026, 4, 30)
    assert result[7] == 1