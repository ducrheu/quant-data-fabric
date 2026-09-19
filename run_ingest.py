"""Manual run: ingest whole-market daily bars for the universe, day by day.

用法：
    python run_ingest.py        # 全部交易日
    python run_ingest.py 5      # 只处理前 5 个交易日（试跑）

断点恢复靠"再跑一次"：成功过的日子由 ingest_log 跳过，失败的下次重跑。
"""

import sys
import time

import tushare as ts

from src.config import get_tushare_token
from src.connectors.price_connector import TusharePriceConnector
from src.normalizers.price import TusharePriceNormalizer
from src.pipelines.price import PricePipeline
from src.repositories.ingest_log import IngestLogRepository
from src.repositories.price import PriceRepository
from src.universe import load_universe
from src.trading_calendar import load_trading_days, to_date

SOURCE = "tushare"
REQUEST_INTERVAL_SECONDS = 0.3
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS =5

def ingest_one(pipeline, symbols, trade_date):
    """带重试的摄入一天 返回(result, error)；(None, error) 表示这天没成功
    空返回也算失败 —— 有交易的交易日不可能空
    """
    error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = pipeline.run_market(trade_date, symbols)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        else:
            if result.market_rows == 0:
                error = "empty market response"
            else:
                return result, None

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS * attempt)

    return None, error

def reconcile(price_repo, log_repo):
    """对账：日志说成功的日子，价格表里必须要有数据"""
    logged = {day.strftime("%Y%m%d") for day in log_repo.done_dates(SOURCE)}
    stored = {
        row[0].strftime("%Y%m%d")
        for row in price_repo.con.execute(
            "SELECT DISTINCT trade_time FROM price_daily"
        ).fetchall()
    }

    print("=== reconcile ===")
    print(f"logged success     : {len(logged)}")
    print(f"days in price_daily: {len(stored)}")
    print(f"logged but missing : {sorted(logged - stored)[:5]}")
    print(f"stored but unlogged: {sorted(stored - logged)[:5]}")

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    pro = ts.pro_api(get_tushare_token())

    connector = TusharePriceConnector(pro)
    normalizer = TusharePriceNormalizer()
    price_repo = PriceRepository()
    log_repo = IngestLogRepository()
    pipeline = PricePipeline(connector, normalizer, price_repo)

    symbols = load_universe()
    dates = load_trading_days()

    done = log_repo.done_dates(SOURCE)
    todo = [day for day in dates if to_date(day) not in done]
    if limit is not None:
        todo = todo[:limit]

    print(f"universe={len(symbols)} dates={len(dates)} done={len(done)} todo={len(todo)}")
    ok = 0
    failed = 0

    for index, trade_date in enumerate(todo, start = 1):
        day = to_date(trade_date)

        result, error = ingest_one(pipeline, symbols, trade_date)

        if result is None:
            failed += 1
            log_repo.record(
                day, SOURCE, "failed",
                market_rows = 0,
                kept = 0, saved = 0, skipped = 0, failed = 0,
                error = error
            )
            print(f"[{index}/{len(todo)}] {trade_date} FAILED {error}")
        else:
            ok += 1
            log_repo.record(
                day, SOURCE, "success",
                market_rows = result.market_rows,
                kept = result.total,
                saved = result.saved,
                skipped = result.skipped,
                failed = result.failed,
                error = None,
            )
            print(
                f"[{index}/{len(todo)}] {trade_date} ok "
                f"market={result.market_rows} kept={result.total} "
                f"saved={result.saved} skipped={result.skipped} failed={result.failed}"
            )

        time.sleep(REQUEST_INTERVAL_SECONDS)

    print(f"finished: ok={ok}, failed={failed}")
    reconcile(price_repo, log_repo)
    price_repo.close()
    log_repo.close()

if __name__ == "__main__":
    main()