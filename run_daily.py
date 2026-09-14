"""
Manual run: ingest daily prices for the whole universe.

Requires TUSHARE_TOKEN in .env and network access.
This is a manual script, not a pytest test (tests must stay offline).
"""

import time

import tushare as ts

from src.config import get_tushare_token
from src.connectors.price_connector import TusharePriceConnector
from src.normalizers.price import TusharePriceNormalizer
from src.pipelines.price import PricePipeline
from src.repositories.price import PriceRepository
from src.universe import SYMBOLS

def print_result(result):
    print(f"total: {result.total}")
    print(f"saved: {result.saved}")
    print(f"skipped: {result.skipped}")
    print(f"failed: {result.failed}")
    for err in result.errors:
        print(f"error: {err}")

START_DATE = "20250101"
END_DATE = "20260913"
REQUEST_INTERVAL_SECONDS = 0.3

def main():
    pro = ts.pro_api(get_tushare_token())

    connector = TusharePriceConnector(pro)
    normalizer = TusharePriceNormalizer()
    repository = PriceRepository()

    pipeline = PricePipeline(connector, normalizer, repository)

    ok = 0
    failed = 0

    for symbol in SYMBOLS:
        try:
            result = pipeline.run(symbol, START_DATE, END_DATE)
            print(
                f"{symbol} total={result.total} saved={result.saved}"
                f"skipped={result.skipped} failed={result.failed}"
            )
            ok += 1
        except Exception as exc:
            print(f"{symbol} ERROR: {exc}")
            failed += 1

        time.sleep(REQUEST_INTERVAL_SECONDS)

    print(f"completed: ok={ok}, failed={failed}, symbols={len(SYMBOLS)}")
    repository.close() 

if __name__ == "__main__":
    main()