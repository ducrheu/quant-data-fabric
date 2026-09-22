"""Manual research script: evaluate the momentum factor.

Computes forward returns, the information coefficient (IC) and quantile
returns for mom_20d over the current universe.

This is exploratory research code: it reads from DuckDB and prints
results. When a factor looks promising, the logic gets moved into src/
with proper tests.
"""

import duckdb
import pandas as pd
from pandas.core.array_algos import quantile

from src.factors.evaluate import rank_ic, sample_every, t_stat, quantile_returns, long_short_spread
from src.config import FACTOR_DB_PATH, PRICE_DB_PATH

PRICE_DB = PRICE_DB_PATH
FACTOR_DB = FACTOR_DB_PATH
FACTOR_NAME = "mom_20d"
HORIZON = 20
QUANTILES = 5

def load_prices() -> pd.DataFrame:
    con = duckdb.connect(PRICE_DB, read_only = True)
    frame = con.execute(
        """
        SELECT symbol, trade_time, close
        FROM price_daily
        ORDER BY symbol, trade_time
        """
    ).fetch_df()
    con.close()
    return frame

def load_factors() -> pd.DataFrame:
    con = duckdb.connect(FACTOR_DB, read_only = True)
    frame = con.execute(
        """
        SELECT symbol, trade_time, value
        FROM factor_daily
            WHERE factor_name = ?
            ORDER BY symbol, trade_time
        """,
        [FACTOR_NAME],
    ).fetch_df()
    con.close()
    return frame

def main():
    prices = load_prices()
    factors = load_factors()

    prices["forward_close"] = prices.groupby("symbol")["close"].shift(-HORIZON)
    prices["forward_return"] = prices["forward_close"] / prices["close"] - 1.0

    data = factors.merge(
        prices[["symbol", "trade_time", "forward_return"]],
        on = ["symbol", "trade_time"],
        how = "inner",
    ).dropna(subset = ["forward_return"])

    print(
        f"rows={len(data)} dates={data['trade_time'].nunique()} "
        f"symbols={data['symbol'].nunique()}"
    )

    ic = rank_ic(data)

    print("=== IC (rank) ===")
    print(f"n: {len(ic)}")
    print(f"mean : {ic.mean():+.4f}")
    print(f"std : {ic.std():+.4f}")
    print(f"IC>0 : {(ic > 0).mean():.1%}")

    sampled = sample_every(ic, HORIZON)

    print("=== significance ===")
    print(f"naive t   (overlap, 不可信) : {t_stat(ic):+.2f}")
    print(f"non-overlap n={len(sampled)} mean={sampled.mean():+.4f} "
          f"t={t_stat(sampled):+.2f}")

    quantiles = quantile_returns(data, QUANTILES)

    print("=== quantile mean forward return ===")
    for bucket, value in quantiles.mean().items():
        print(f" Q{int(bucket) + 1}: {value:+.4f}")

    spread = long_short_spread(quantiles)
    sampled_spread = sample_every(spread, HORIZON)

    print("=== long-short spread (Q5 - Q1) ===")
    print(f"mean : {spread.mean():+.4f}  std: {spread.std():+.4f}")
    print(f"naive t   (overlap, 不可信) : {t_stat(spread):+.2f}")
    print(f"non-overlap n={len(sampled_spread)} mean={sampled_spread.mean():+.4f} "
          f"t={t_stat(sampled_spread):+.2f}")

if __name__ == "__main__":
    main()