"""Manual run: 用 baostock 回填 daily_basic（收盘 / 换手 / PE / PB），按证券拉区间。

用法：
    python run_daily_basic_backfill.py        # 全部 300 只
    python run_daily_basic_backfill.py 10     # 只做前 10 只（试跑）

幂等：唯一键 (symbol, trade_time, source)，重复跑不会多出行。
不建断点表：300 次调用约 3–5 分钟，重跑即可；失败的下次自动补。

注意：baostock 的日线不提供 total_mv / circ_mv，这两列为 NULL。
"""

import sys
import time

import baostock as bs

from src.config import PRICE_DB_PATH
from src.connectors.baostock_daily_basic_connector import BaostockDailyBasicConnector
from src.normalizers.baostock_daily_basic import BaostockDailyBasicNormalizer
from src.normalizers.baostock_financial import to_bs_code
from src.repositories.daily_basic import DailyBasicRepository
from src.trading_calendar import load_trading_days, to_date
from src.universe import load_universe
from src.validators.baostock_daily_basic import validate_baostock_daily_basic_raw

import socket
socket.setdefaulttimeout(30)

SOURCE = "baostock"
REQUEST_INTERVAL_SECONDS = 0.5
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 5
QUOTA_MARKERS = ("频率", "权限", "积分", "登录", "网络")

def is_quota_stop(error: str) -> bool:
    """配额 / 权限 / 登录类错误：继续跑没有意义，应当提前停下。"""
    return any(marker in error for marker in QUOTA_MARKERS)

def ingest_one(connector, normalizer, repository, symbol, start_date, end_date):
    """拉一只票的区间、返回（raw_count, kept, saved, failed, error）"""
    error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raws = connector.fetch_daily_basic(to_bs_code(symbol), start_date, end_date)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        else:
            records = []
            failed = 0
            for raw in raws:
                if validate_baostock_daily_basic_raw(raw):
                    failed += 1
                    continue
                records.append(normalizer.normalize(raw))

            saved = repository.save_many(records)
            return len(raws), len(records), saved, failed, None

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS * attempt)

    return 0, 0, 0, 0, error

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    login = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            login = bs.login()
        except Exception as exc:
            print(f"login attempt {attempt} failed: {type(exc).__name__}: {exc}")
        else:
            if login.error_code == "0":
                break
            print(f"login attempt {attempt}: {login.error_code} {login.error_msg}")

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS * attempt)
    else:
        print("baostock login failed after retries")
        sys.exit(1)

    repository = DailyBasicRepository(PRICE_DB_PATH)
    try:
        connector = BaostockDailyBasicConnector(bs)
        normalizer = BaostockDailyBasicNormalizer()

        days = load_trading_days()
        start_date = to_date(days[0]).isoformat()
        end_date = to_date(days[-1]).isoformat()

        symbols = sorted(load_universe())
        if limit is not None:
            symbols = symbols[:limit]

        print(f"symbols={len(symbols)} range={start_date}~{end_date} source={SOURCE}")

        ok = 0
        failed = 0

        for index, symbol in enumerate(symbols, start=1):
            raw_count, kept,saved, bad, error = ingest_one(
                connector, normalizer, repository, symbol, start_date, end_date
            )

            if error is not None:
                failed += 1
                print(f"[{index} / {len(symbols)}] {symbol} FAILED {error}")

                if is_quota_stop(error):
                    print("检测到配额 / 权限 / 登录受限，提前停止。已写入的数据保留，下次重跑自动补齐。")
                    break

            else:
                ok += 1
                print(
                    f"[{index}/{len(symbols)}] {symbol} raw={raw_count} "
                    f"kept={kept} saved={saved} bad={bad}"
                )

            time.sleep(REQUEST_INTERVAL_SECONDS)

        print(f"finished: ok={ok}, failed={failed}")
    finally:
        repository.close()
        bs.logout()

if __name__ == "__main__":
    main()