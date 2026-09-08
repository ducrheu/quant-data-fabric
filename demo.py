"""Quant Data Fabric V0.1 demo: run the ingestion pipeline with fake data."""

from datetime import datetime
import pandas as pd
from src.connectors.tushare_connector import TushareConnector
from src.normalizers.financial import TushareFinancialNormalizer
from src.pipelines.financial import FinancialPipeline
from src.repositories.financial import FinancialRepository

class DemoClient:
    """Quant Data Fabric 0.1 demo"""
    def income(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "n_income": 80000000000,
                    "end_date": "20251231",
                    "ann_date": "20260430",
                },
                {
                    "ts_code": ts_code,
                    "n_income": "not-a-number",
                    "end_date": "20251231",
                    "ann_date": "20260430",
                },
            ]
        )

def main():
    connector = TushareConnector(DemoClient())
    normalizer = TushareFinancialNormalizer()
    repository = FinancialRepository("data/quant_data.duckdb")

    pipeline = FinancialPipeline(connector, normalizer, repository)

    result = pipeline.run(
        ts_code="600519.SH",
        start_date="20250101",
        end_date="20251231",
    )

    print("==========Pipeline Query========")
    print(f"total: {result.total}")
    print(f"saved: {result.saved}")
    print(f"failed: {result.failed}")
    for err in result.errors:
        print(f"  error: {err}")

    pit = repository.get_pit(
        "600519.SH",
        "net_income",
        datetime(2026, 5, 10)
    )

    print("========PIT Query========")
    print(pit)

    repository.close()

if __name__ == "__main__":
    main()