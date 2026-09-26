"""Quant Data Fabric 离线 demo：零网络、假数据，演示 PIT 的四条核心保证。

跑法：
    python demo.py

每次运行都新建一个临时数据库，因此输出的数字与提交进 git 的样例
永远一致（可复现）。
"""

from datetime import datetime
import os
import tempfile

import pandas as pd

from src.connectors.tushare_connector import TushareConnector
from src.normalizers.financial import TushareFinancialNormalizer
from src.pipelines.financial import FinancialPipeline
from src.repositories.financial import FinancialRepository

# 第一批抓取：1行正常 + 1行坏数据
GOOD_AND_BAD_ROWS = [
{
        "n_income": 80000000000,
        "end_date": "20251231",
        "ann_date": "20260430",
    },
    {
        "n_income": "not-a-number",
        "end_date": "20251231",
        "ann_date": "20260430",
    },
]

# 第二批抓取：同一报告期的更正公告（重述）
RESTATEMENT_ROWS = [
    {
"n_income": 78000000000,
        "end_date": "20251231",
        "ann_date": "20260615",
    },
]

class DemoClient:
    """假 Tushare 客户端：返回构造时给定的一批 rows"""
    def __init__(self, rows):
        self.rows = rows

    def income(self, ts_code, start_date, end_date):
        return pd.DataFrame([{**row, "ts_code": ts_code} for row in self.rows])

def build_pipeline(rows, repository):
    """用给定的假数据 + 同一个真实仓库, 拼一条摄入链"""
    return FinancialPipeline(
        TushareConnector(DemoClient(rows)),
        TushareFinancialNormalizer(),
        repository,
    )

def run_once(pipeline, tag):
    result = pipeline.run(
        ts_code = "600519.SH",
        start_date = "20250101",
        end_date = "20251231",
    )
    print(
        f"  {tag}: total={result.total} saved={result.saved} "
        f"restated={result.restated} skipped={result.skipped} failed={result.failed}"
    )
    for err in result.errors:
        print(f"    error: {err}")
    return result

def show(row):
    if row is None:
        return "None <- 这条数据当时还不存在"
    return f"{row[2] / 1e8:.1f} 亿元 (available_time={row[4]:%Y-%m-%d})"

def main():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repository = FinancialRepository(os.path.join(tmp_dir, "demo.duckdb"))
        print("=" * 64)
        print("[1] 部分成功：坏行只被跳过，好行正常入库")
        print("=" * 64)
        run_once(build_pipeline(GOOD_AND_BAD_ROWS, repository), "First time")

        print()
        print("=" * 64)
        print("[2] 幂等：同一批数据再跑一次，saved=0")
        print("=" * 64)
        run_once(build_pipeline(GOOD_AND_BAD_ROWS, repository), "Second time")

        print()
        print("=" * 64)
        print("[3] PIT 闸门：披露前查不到，披露后查得到")
        print("=" * 64)
        print(" 数据：600519.SH 2025年报 net_income = 800 亿元：2026-04-30 披露")

        before = repository.get_pit("600519.SH", "net_income", datetime(2026, 3, 1))
        after = repository.get_pit("600519.SH", "net_income", datetime(2026, 5, 10))

        print(f"    as_of = 2026-03-01(披露前) -> {show(before)}")
        print(f"    as_of = 2026-05-10(披露后) -> {show(after)}")

        print()
        print("=" * 64)
        print("[4] 重述：同一报告期的新披露 = 新版本共存，历史不被改写")
        print("=" * 64)
        print(" 数据：2026-06-15 更正公告，net_income 由 800 亿改为 780 亿")

        run_once(build_pipeline(RESTATEMENT_ROWS, repository), "Restatement")

        rows_in_db = repository.con.execute(
            "SELECT COUNT(*) FROM financial_fact WHERE symbol = '600519.SH'"
        ).fetchone()[0]
        print(f"    financial_fact 中该股票共 {rows_in_db} 条（两个版本都留着）")

        history = repository.get_pit("600519.SH", "net_income", datetime(2026, 5, 10))
        latest = repository.get_pit("600519.SH", "net_income", datetime(2026, 7, 1))

        print(f"    as_of = 2026-05-10(重述前) -> {show(history)}")
        print(f"    as_of = 2026-07-01(重述后) -> {show(latest)}")

        repository.close()
if __name__ == "__main__":
    main()