"""Baostock 日频估值数据归一化。

复用财务域那两个方向映射：to_ts_code 让 `sh.600519` → `600519.SH` 只写一次。

空字符串必须转 None：baostock 在缺失值时给的是 `""`，不是 NULL。
"""

from datetime import datetime

from src.domain.daily_basic import DailyBasicRecord
from src.normalizers.base import BaseNormalizer
from src.normalizers.baostock_financial import to_ts_code

def to_float(value) -> float | None:
    """baostock 的缺失值是空字符串，不是 NULL。"""
    if value is None or value == "":
        return None
    return float(value)

class BaostockDailyBasicNormalizer(BaseNormalizer):
    def normalize(self, raw):
        data = raw.raw_data

        return DailyBasicRecord(
            symbol=to_ts_code(data["code"]),
            trade_time=datetime.strptime(data["date"], "%Y-%m-%d"),
            close=to_float(data.get("close")),
            turnover_rate=to_float(data.get("turn")),
            total_mv=None,
            circ_mv=None,
            pe_ttm=to_float(data.get("peTTM")),
            pb=to_float(data.get("pbMRQ")),
            source=raw.source,
        )