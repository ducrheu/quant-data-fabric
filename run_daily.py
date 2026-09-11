"""Manual end-to-end run: ...
This is a manual script, not a pytest test (tests must stay offline).
"""

import tushare as ts

from src.config import get_tushare_token
from src.connectors.price_connector import TusharePriceConnector
from src.normalizers.price import TusharePriceNormalizer
from src.pipelines.price import PricePipeline
from src.repositories.price import PriceRepository

def print_result(result):
    print(f"total: {result.total}")
    print(f"saved: {result.saved}")
    print(f"skipped: {result.skipped}")
    print(f"failed: {result.failed}")
    for err in result.errors:
        print(f"error: {err}")

def main():
    pro = ts.pro_api(get_tushare_token())

    connector = TusharePriceConnector(pro)
    normalizer = TusharePriceNormalizer()
    repository = PriceRepository()

    pipeline = PricePipeline(connector, normalizer, repository)

    ts_code = "600519.SH"
    start_date = "20260101"
    end_date = "20260131"

    print("=== Run 1 ===")
    result = pipeline.run(ts_code, start_date, end_date)
    print_result(result)

    print("=== Run 2 (same params)===")
    result = pipeline.run(ts_code, start_date, end_date)
    print_result(result)

    rows = repository.con.execute(
        "SELECT COUNT(*) FROM price_daily WHERE symbol = ?",
        [ts_code],
    ).fetchone()[0]
    print(f"rows in database: {rows}")

    repository.close()

if __name__ == "__main__":
    main()