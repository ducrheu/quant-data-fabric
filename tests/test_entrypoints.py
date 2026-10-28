"""顶层入口冒烟测试。

pytest 只收集 tests/ 下的 test_*.py；顶层脚本（demo.py / demo_replay.py / run_*.py）
不在收集范围内，所以它们坏了测试也不会红——步 2 就吃过这个亏
（pytest 全绿、demo.py 炸 TypeError）。

这里只验证「能不能跑完 + 关键输出在不在」，不重复业务逻辑（那是单元测试的活）。
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRICE_DB = PROJECT_ROOT / "data" / "price.duckdb"
FACTOR_DB = PROJECT_ROOT / "data" / "factor.duckdb"

def run_script(name, timeout=120):
    """在项目根目录、用当前解释器跑一个顶层脚本。"""
    env = dict(os.environ)
    env["PYTHONDONRWRITEBYTECODE"] = "1"

    return subprocess.run(
        [sys.executable, name],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

def require_databases():
    if not (PRICE_DB.exists() and FACTOR_DB.exists()):
        pytest.skip("本地 DuckDB 不存在（数据不进 git，需要先建库）")

def test_demo_runs_offline():
    """零依赖入口：clone 下来就该能跑完 5 段"""
    result = run_script("demo.py")

    assert result.returncode == 0, result.stderr

    for marker in ("[1] 部分成功", "[2] 幂等", "[3] PIT 闸门", "[4] 重述", "[5] 血缘"):
        assert marker in result.stdout


def test_demo_replay_runs_against_real_databases():
    require_databases()

    result = run_script("demo_replay.py")

    assert result.returncode == 0, result.stderr
    assert "对账通过" in result.stdout
    assert "[4] 财务域" in result.stdout


def test_run_analysis_finishes():
    require_databases()

    result = run_script("run_analysis.py")

    assert result.returncode == 0, result.stderr
    assert "=== IC (rank) ===" in result.stdout
    assert "Newey-West" in result.stdout


def test_run_backtest_finishes():
    require_databases()

    result = run_script("run_backtest.py")

    assert result.returncode == 0, result.stderr
    assert "=== per-period long-short" in result.stdout