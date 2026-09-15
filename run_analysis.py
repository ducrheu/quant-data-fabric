"""Manual research script: evaluate the momentum factor.

Computes forward returns, the information coefficient (IC) and quantile
returns for mom_20d over the current universe.

This is exploratory research code: it reads from DuckDB and prints
results. When a factor looks promising, the logic gets moved into src/
with proper tests.
"""

import duckdb
import pandas as pd
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

    ic = data.groupby("trade_time").apply(
        lambda group: group["value"].corr(group["forward_return"], method="spearman")
    )
    print("=== IC (rank) ===")
    print(f"mean : {ic.mean():+.4f}")
    print(f"std : {ic.std():+.4f}")
    print(f"IC>0 : {(ic > 0).mean():.1%}")

    data = data.copy()

    data["bucket"] = data.groupby("trade_time")["value"].transform(
        lambda series: pd.qcut(series.rank(method="first"), QUANTILES, labels=False)
    )

    per_date = data.groupby(["trade_time", "bucket"])["forward_return"].mean()
    means = per_date.groupby(level="bucket").mean()

    print("=== quantile mean forward return ===")
    for bucket, value in means.items():
        print(f" Q{int(bucket) + 1}: {value:+.4f}")
    print(f" Q5-Q1 spread: {means.iloc[-1] - means.iloc[0]:+.4f}")

if __name__ == "__main__":
    main()