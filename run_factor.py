"""Manual run: compute momentum factors from stored price data."""

import statistics
from datetime import datetime

from src.pipelines.factor import MomentumFactorPipeline
from src.repositories.factor import FactorRepository
from src.repositories.price import PriceRepository
from src.trading_calendar import load_trading_days
from src.universe import load_universe
from src.universe import SYMBOLS

WINDOW = 20
FACTOR_NAME = "mom_20d"
PROGRESS_EVERY = 50

def main():
    price_repo = PriceRepository("data/price.duckdb")
    factor_repo = FactorRepository("data/factor.duckdb")

    pipeline = MomentumFactorPipeline(price_repo, factor_repo)

    symbols = sorted(load_universe())
    start_time = datetime(2025, 1, 1)
    end_time = datetime.strptime(load_trading_days()[-1], "%Y%m%d")

    total = saved = skipped = 0

    for index, symbol in enumerate(symbols, start = 1):
        result = pipeline.run(symbol, start_time, end_time, WINDOW)
        total += result.total
        saved += result.saved
        skipped += result.skipped

        if index % PROGRESS_EVERY == 0:
            print(f"[{index} / {len(symbols)}] total={total}"
                  f"saved={saved} skipped={skipped}")

    print("=== summary ===")
    print(f"symbols processed : {index}/{len(symbols)}")
    print(f"total={total} saved={saved} skipped={skipped}")
    print(f"total == saved + skipped : {total == saved + skipped}")

    stored = {
        row[0] for row in factor_repo.con.execute(
            "SELECT DISTINCT symbol FROM factor_daily WHERE factor_name = ?",
            [FACTOR_NAME],
        ).fetchall()
    }
    rows = factor_repo.con.execute(
        "SELECT COUNT(*) FROM factor_daily WHERE factor_name = ?",
        [FACTOR_NAME],
    ).fetchone()[0]

    print("=== db truth ===")
    print(f"factor_daily rows={rows} symbols={len(stored)}")
    missing = sorted(set(symbols) - stored)
    print(f"universe 里没有因子的票: {len(missing)} 只 {missing[:5]}")

    price_repo.close()
    factor_repo.close()

if __name__ == "__main__":
    main()