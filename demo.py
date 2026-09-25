"""Quant Data Fabric 离线 demo：零网络、假数据，演示 PIT 的三条核心保证。

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


class DemoClient:
    """假 Tushare 客户端：2行 -- 1 行正常， 1 行坏数据"""
    def income(self, ts_code, start_date, end_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": ts_code,
                    "n_income": 80000000000,
                    "end_date": "20251231",
                    "ann_date": "20260430",
                },
                {
                    "ts_code": ts_code,
                    "n_income": "not-a-number",
                    "end_date": "20251231",
                    "ann_date": "20260430",
                },
            ]
        )

def run_once(pipeline, tag):
    result = pipeline.run(
        ts_code = "600519.SH",
        start_date = "20250101",
        end_date = "20251231",
    )
    print(
        f"  {tag}: total={result.total} saved={result.saved} "
        f"skipped={result.skipped} failed={result.failed}"
    )
    for err in result.errors:
        print(f"    error: {err}")
    return result

def show(row):
    if row is None:
        return "None <- 当时这条数据还不存在"
    return f"{row[2] / 1e8:.1f} 亿元 (available_time={row[4]:%Y-%m-%d})"

def main():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repository = FinancialRepository(os.path.join(tmp_dir, "demo.duckdb"))
        pipeline = FinancialPipeline(
            TushareConnector(DemoClient()),
            TushareFinancialNormalizer(),
            repository,
        )

        print("=" * 64)
        print("[1] 部分成功：坏行只被跳过，好行正常入库")
        print("=" * 64)
        run_once(pipeline, "First time")

        print()
        print("=" * 64)
        print("[2] 幂等：同一批数据再跑一次，saved=0")
        print("=" * 64)
        run_once(pipeline, "Second time")

        print()
        print("=" * 64)
        print("[3] PIT 闸门：披露前查不到，披露后查得到")
        print("=" * 64)
        print(" 数据：600519.SH 2025年报 net_income = 800 亿元：2026-04-30 披露")

        before = repository.get_pit(
            "600519.SH", "net_income", datetime(2026, 3, 1)
        )
        after = repository.get_pit(
            "600519.SH", "net_income", datetime(2026, 5, 10)
        )

        print(f"    as_of = 2026-03-01(披露前) -> {show(before)}")
        print(f"    as_of = 2026-05-10(披露后) -> {show(after)}")

        repository.close()

if __name__ == "__main__":
    main()