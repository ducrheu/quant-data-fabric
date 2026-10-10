"""Manual run: ingest daily_basic (市值 / 换手 / 估值) for the universe, day by day.

用法：
    python run_daily_basic.py        # 全部交易日
    python run_daily_basic.py 5      # 只处理前 5 个待办交易日（试跑）

断点恢复靠"再跑一次"：成功过的日子由 ingest_log 跳过，失败的下次重跑。
撞到配额 / 权限限制时**主动停下**，不会把剩余日期刷成失败。

该接口限频 1 次/分钟，所以每次调用之间睡 62 秒；417 天约需 7 小时。
随时可以 Ctrl-C，下次运行会自动续上。
"""

import sys
import time
from datetime import datetime

import tushare as ts

from src.config import get_tushare_token
from src.domain.daily_basic import DailyBasicRecord
from src.repositories.daily_basic import DailyBasicRepository
from src.repositories.ingest_log import IngestLogRepository
from src.trading_calendar import load_trading_days, to_date
from src.universe import load_universe

SOURCE = "tushare.daily_basic"
REQUEST_INTERVAL_SECONDS = 62
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 62
QUOTA_MARKERS = ("频率超限", "没有接口", "权限")

def as_number(value):
    """Tushare 的缺失值是 NaN；统一转成 None。"""
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return None if number != number else number

def is_quota_stop(error: str) -> bool:
    """配额 / 权限类错误：继续跑没有意义，应当提前停下。"""
    return any(marker in error for marker in QUOTA_MARKERS)

def to_records(frame, symbols):
    """原始一帧 → 领域记录；只保留池内股票。"""
    records = []
    for _, row in frame.iterrows():
        symbol = row["ts_code"]
        if symbol not in symbols:
            continue

        records.append(
            DailyBasicRecord(
                symbol=symbol,
                trade_time=datetime.strptime(row["trade_date"], "%Y%m%d"),
                close=as_number(row.get("close")),
                turnover_rate=as_number(row.get("turnover_rate")),
                total_mv=as_number(row.get("total_mv")),
                circ_mv=as_number(row.get("circ_mv")),
                pe_ttm=as_number(row.get("pe_ttm")),
                pb=as_number(row.get("pb")),
                source=SOURCE,
            )
        )
    return records

def pull_one(client, repository, trade_date, symbols):
    """带重试地拉一天。返回 (market_rows, kept, saved, error)。"""
    error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            frame = client.daily_basic(trade_date=trade_date)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        else:
            if frame is None or frame.empty:
                error = "empty response"
            else:
                records = to_records(frame, symbols)
                saved = repository.save_many(records)
                return len(frame), len(records), saved, None

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS * attempt)

    return 0, 0, 0, error

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    client = ts.pro_api(get_tushare_token())
    repository = DailyBasicRepository()
    log_repo = IngestLogRepository()

    symbols = load_universe()
    dates = load_trading_days()

    done = log_repo.done_dates(SOURCE)
    todo = [day for day in dates if day not in done]
    if limit is not None:
        todo = todo[:limit]

    print(f"universe={len(symbols)} dates={len(dates)} done={len(done)} todo={len(todo)}")

    ok = 0
    failed = 0

    for index, trade_date in enumerate(todo, start=1):
        market_rows, kept, saved, error = pull_one(client, repository, trade_date, symbols)

        if error is not None:
            failed += 1
            log_repo.record(
                to_date(trade_date), SOURCE, "failed",
                market_rows=market_rows, kept=kept, saved=saved, skipped=0, failed=1,
                error=error,
            )
            print(f"[{index}/{len(todo)}] {trade_date} FAILED {error}")

            if is_quota_stop(error):
                print("检测到配额 / 权限受限，提前停止。已成功的日子已记账，下次运行自动续上。")
                break

        else:
            ok += 1
            log_repo.record(
                to_date(trade_date), SOURCE, "success",
                market_rows=market_rows, kept=kept, saved=saved, skipped=kept - saved, failed=0, error=None,
            )
            print(
                f"[{index}/{len(todo)}] {trade_date} ok "
                f"market={market_rows} kept={kept} saved={saved}"
            )

        time.sleep(REQUEST_INTERVAL_SECONDS)

    print(f"finished: ok={ok}, failed={failed}")
    repository.close()
    log_repo.close()

if __name__ == "__main__":
    main()