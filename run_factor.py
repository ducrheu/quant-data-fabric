"""Manual run: compute momentum factors from stored price data."""

import statistics
from datetime import datetime

from src.pipelines.factor import MomentumFactorPipeline
from src.repositories.factor import FactorRepository
from src.repositories.price import PriceRepository
from src.universe import SYMBOLS

def main():
    price_repo = PriceRepository("data/price.duckdb")
    factor_repo = FactorRepository("data/factor.duckdb")

    pipeline = MomentumFactorPipeline(price_repo, factor_repo)

    window = 20
    start_time = datetime(2025, 1, 1)
    end_time = datetime(2026, 9, 13)

    for symbol in SYMBOLS:
        result = pipeline.run(symbol, start_time, end_time, window)

        # print("=== Factor run ===")
        print(f"total: {result.total}")
        print(f"saved: {result.saved}")
        print(f"skipped: {result.skipped}")

        series = factor_repo.get_series(
            symbol,
            f"mom_{window}d",
            start_time,
            end_time,
        )

        print(f"=== mom_{window}d ===")
        print(f"count: {len(series)}")

        if series:
            values = [record.value for record in series]
            print(f"min: {min(values):+.4f}")
            print(f"max: {max(values):+.4f}")
            print(f"mean: {statistics.mean(values):+.4f}")
            print(f"stdev : {statistics.stdev(values):.4f}")

            print("last 5:")
            for record in series[-5:]:
                print(f"  {record.trade_time.date()}  {record.value:+.4f}")

    price_repo.close()
    factor_repo.close()

if __name__ == "__main__":
    main()