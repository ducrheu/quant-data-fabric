"""股票池（universe）：快照的读写，以及可复现的抽样。

池子本身也是"时点相关"的数据 —— 拿今天的成分股回到过去回测，
等于让未来的信息泄漏进过去（幸存者偏差）。所以池子必须落成带出处的快照。
"""

import json
import random
from pathlib import Path

UNIVERSE_PATH = "data/universe.json"

SYMBOLS = [
    "600519.SH",   # 贵州茅台
    "000858.SZ",   # 五粮液
    "601318.SH",   # 中国平安
    "600036.SH",   # 招商银行
    "000333.SZ",   # 美的集团
    "600276.SH",   # 恒瑞医药
    "002415.SZ",   # 海康威视
    "600030.SH",   # 中信证券
    "601166.SH",   # 兴业银行
    "000001.SZ",   # 平安银行
]

def select_universe(candidates, size, seed):
    """无放回随机抽size只 先排序再抽，保证结果与输入顺序无关"""
    if size <= 0:
        raise ValueError("Size must be positive")

    unique = sorted(set(candidates))
    if size > len(unique):
        raise ValueError(f"size {size} exceeds {len(unique)} candidates")

    picked = random.Random(seed).sample(unique, size)
    return sorted(picked)

def save_universe(symbols, as_of, seed, candidates, path = UNIVERSE_PATH):
    payload = {
        "as_of": as_of,
        "size": len(symbols),
        "seed": seed,
        "candidates": candidates,
        "source": "tushare.daily",
        "symbols": list(symbols),
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def load_universe(path=UNIVERSE_PATH):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return set(payload["symbols"])