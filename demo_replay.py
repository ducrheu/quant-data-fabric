"""Quant Data Fabric 真实库回放：只读打开本地 DuckDB，打印规模与对账。

跑法：
    python demo_replay.py

前提（数据不进 git，每台机器要自己建）：
    python run_universe.py     # 股票池 + 交易日历快照
    python run_ingest.py       # 按交易日摄入全市场行情
    python run_factor.py       # 由行情派生 mom_20d
    python run_financial_backfill.py   # 用 baostock 回填财务季频数据

注意：本脚本以 read_only=True 打开数据库，绝不写入。
"""

import os
import sys
from datetime import datetime

import duckdb

from src.config import FACTOR_DB_PATH, PRICE_DB_PATH, PRICE_SOURCE, FINANCIAL_DB_PATH

def connect_read_only(path):
    """只读连接：缺库时给出可执行的补救命令，而不是抛栈"""
    if not os.path.exists(path):
        print(f"缺少 {path}")
        print("  python run_universe.py")
        print("  python run_ingest.py")
        print("  python run_factor.py")
        print("  python run_financial_backfill.py")
        sys.exit(1)
    return duckdb.connect(path, read_only=True)

def main():
    price_con = connect_read_only(PRICE_DB_PATH)
    factor_con = connect_read_only(FACTOR_DB_PATH)

    print("=" * 64)
    print("[1] 数据规模 （实测）")
    print("=" * 64)
    rows, days, symbols = price_con.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT trade_time), COUNT(DISTINCT symbol)
        FROM price_daily
        """
    ).fetchone()
    factor_rows, factor_symbols = factor_con.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT symbol)
        FROM factor_daily
        """
    ).fetchone()
    print(f"    price_daily : {rows:,} 行 / {days} 个交易日 / {symbols} 只股票")
    print(f"    factor_daily: {factor_rows:,} 行 / {factor_symbols} 只股票")

    print()
    print("=" * 64)
    print("[2] 摄入对账：日志说的 VS 表里实际有的")
    print("=" * 64)
    try:
        log_days, log_saved = price_con.execute(
            """
            SELECT COUNT(*), SUM(saved)
            FROM ingest_log
            WHERE status = 'success' AND source = ?
            """,
            [PRICE_SOURCE],
        ).fetchone()
    except duckdb.Error as exc:
        print(f"    ingest_log 不可用: {exc}")
        print("     -> 先跑 python run_ingest.py")
        sys.exit(1)

    print(f"    ingest_log : success {log_days} 天, 累计 saved {log_saved:,} 行")
    print(f"    price_daily : 实际 {days} 天, {rows:,} 行")

    matched = (log_days == days) and (log_saved == rows)
    print(f"  -> 对账{'通过' if matched else '不一致'}（两个独立来源给出同一个数）")

    print()
    print("=" * 64)
    print("[3] 因子评价")
    print("=" * 64)
    print("  数字见 FINDINGS.md 第 2、4 节，复现命令：")
    print("    python run_analysis.py")
    print("  本脚本不重复实现因子评价，避免同一个数字出现两个实现。")

    print()
    print()
    print("=" * 64)
    print("[4] 财务域：真实数据 + PIT 闸门")
    print("=" * 64)
    if not os.path.exists(FINANCIAL_DB_PATH):
        print(f"    缺少 {FINANCIAL_DB_PATH}")
        print("     -> 先跑 python run_financial_backfill.py")
    else:
        fin_con = duckdb.connect(FINANCIAL_DB_PATH, read_only=True)
        try:
            fact_rows, fact_symbols, fact_sources = fin_con.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT symbol), COUNT(DISTINCT source)
                FROM financial_fact
                """
            ).fetchone()
            first_event, last_event = fin_con.execute(
                "SELECT MIN(event_time), MAX(event_time) FROM financial_fact"
            ).fetchone()
            print(f"    financial_fact: {fact_rows:,} 行 / {fact_symbols} 只 / {fact_sources} 个源")
            print(f"    报告期范围    : {first_event:%Y-%m-%d} ~ {last_event:%Y-%m-%d}")

            print("     实例000551.SZ net_income (2024  年报， 2025-04-08 披露)：")
            for label, as_of in (
                ("披露前", datetime(2025, 4, 7)),
                ("披露后", datetime(2025, 4, 8)),
            ):
                row = fin_con.execute(
                    """
                    SELECT value, available_time
                    FROM financial_fact
                    WHERE symbol = ?
                      AND metric_name = ?
                      AND source = ?
                      AND event_time = ?
                      AND available_time <= ?
                    ORDER BY available_time DESC, revision_id DESC LIMIT 1
                    """,
                    ["000551.SZ", "net_income", "baostock", datetime(2024, 12, 31), as_of],
                ).fetchone()
                if row is None:
                    shown = "None(当时不可得) "
                else:
                    shown = f"{row[0]:,.0f} 元 (available_time={row[1]:%Y-%m-%d}) "
                print(f"        as_of {as_of:%Y-%m-%d} {label} -> {shown}")
        finally:
            fin_con.close()

    price_con.close()
    factor_con.close()

if __name__ == "__main__":
    main()