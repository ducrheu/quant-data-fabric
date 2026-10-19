"""Manual run: 用 baostock 回填财务数据（季频），断点可续。

用法：
    python run_financial_backfill.py            # 全部待办 (code, year, quarter)
    python run_financial_backfill.py 300        # 只做前 300 个待办（试跑，推荐第一次这么跑）

断点恢复靠"再跑一次"：做完的键由 financial_ingest_log 跳过，失败的下次重跑。
撞到配额 / 权限 / 登录类错误时主动停下，不把剩余任务刷成失败。
"""

import sys
import time
from datetime import date

import baostock as bs

from src.config import FINANCIAL_DB_PATH
from src.connectors.baostock_connector import BaostockFinancialConnector
from src.normalizers.baostock_financial import BaostockFinancialNormalizer, to_bs_code
from src.pipelines.financial import FinancialPipeline
from src.repositories.financial import FinancialRepository
from src.repositories.financial_ingest_log import FinancialIngestLogRepository
from src.repositories.ingest_batch import IngestBatchRepository
from src.universe import load_universe
from src.validators.baostock_financial import validate_baostock_profit_raw

SOURCE = "baostock"
API_NAME = "profit"
REQUEST_INTERVAL_SECONDS = 0.5
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 2
QUOTA_MARKERS = ("频率", "权限", "积分", "登录", "网络")

# 回填计划：改这两行就是改规模
YEARS = [2024]
QUARTERS = [4]

QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def is_quota_stop(error: str) -> bool:
    """配额 / 权限 / 登录类错误：继续跑没有意义，应当提前停下。"""
    return any(marker in error for marker in QUOTA_MARKERS)


def stat_date_of(year: int, quarter: int) -> date:
    """请求键 → 报告期。只是便利列，权威值在 financial_fact.event_time。"""
    month, day = QUARTER_END[quarter]
    return date(year, month, day)


def build_tasks(symbols, years, quarters):
    """(code, year, quarter) 任务列表。symbol 按库口径排序，code 转 baostock 口径。"""
    tasks = []
    for symbol in sorted(symbols):
        code = to_bs_code(symbol)
        for year in years:
            for quarter in quarters:
                tasks.append((code, year, quarter))
    return tasks


def pull_one(pipeline, code, year, quarter):
    """带重试地拉一个季度。返回 (result, error)；失败返回 (None, error)。"""
    error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = pipeline.run(code=code, year=year, quarter=quarter)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        else:
            if result.failed > 0:
                error = result.errors[0]
            else:
                return result, None

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS * attempt)

    return None, error


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    login = bs.login()
    if login.error_code != "0":
        print(f"baostock login failed: {login.error_code} {login.error_msg}")
        sys.exit(1)

    try:
        pipeline = FinancialPipeline(
            BaostockFinancialConnector(bs),
            BaostockFinancialNormalizer(),
            FinancialRepository(FINANCIAL_DB_PATH),
            IngestBatchRepository(FINANCIAL_DB_PATH),
            validator=validate_baostock_profit_raw,
            source=SOURCE,
            api_name=API_NAME,
        )
        log_repo = FinancialIngestLogRepository(FINANCIAL_DB_PATH)

        symbols = load_universe()
        tasks = build_tasks(symbols, YEARS, QUARTERS)
        done = log_repo.done_keys(SOURCE)
        todo = [task for task in tasks if task not in done]
        if limit is not None:
            todo = todo[:limit]

        print(f"symbols={len(symbols)} tasks={len(tasks)} done={len(done)} todo={len(todo)}")

        ok = 0
        failed = 0

        for index, (code, year, quarter) in enumerate(todo, start=1):
            result, error = pull_one(pipeline, code, year, quarter)

            if error is not None:
                failed += 1
                log_repo.record(
                    SOURCE, code, year, quarter, "failed",
                    stat_date=None, saved=0, skipped=0, failed=0, error=error,
                )
                print(f"[{index}/{len(todo)}] {code} {year}Q{quarter} FAILED {error}")

                if is_quota_stop(error):
                    print("检测到配额 / 权限 / 登录受限，提前停止。已完成的键已记账，下次运行自动续上。")
                    break
            else:
                status = "empty" if result.total == 0 else "success"
                ok += 1
                log_repo.record(
                    SOURCE, code, year, quarter, status,
                    stat_date=stat_date_of(year, quarter),
                    saved=result.saved, skipped=result.skipped, failed=result.failed,
                    error=None,
                )
                print(
                    f"[{index}/{len(todo)}] {code} {year}Q{quarter} {status} "
                    f"saved={result.saved} skipped={result.skipped}"
                )

            time.sleep(REQUEST_INTERVAL_SECONDS)

        print(f"finished: ok={ok}, failed={failed}")

        pipeline.repository.close()
        pipeline.batch_repository.close()
        log_repo.close()
    finally:
        bs.logout()


if __name__ == "__main__":
    main()
