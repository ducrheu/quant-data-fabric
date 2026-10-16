"""Baostock 财务数据归一化。

两处和 Tushare 路径不同，必须写死在这里：
1. 代码口径：baostock 用 `sh.600519`，库里用 `600519.SH`。
2. 日期口径：baostock 的 pubDate/statDate 是 `YYYY-MM-DD`；Tushare 是 `YYYYMMDD`。

字段口径：
- netProfit = 合并净利润（含少数股东损益），单位：元
- pubDate   = 该报告的首次披露日（2026-10-12 实测）→ 映射到 available_time
"""

from datetime import datetime

from src.domain.financial import FinancialRecord
from src.normalizers.base import BaseNormalizer

def to_ts_code(bs_code:str) -> str:
    """`sh.600519` -> `600519.SH`"""
    market, code = bs_code.split(".")
    return f"{code}.{market.upper()}"

class BaostockFinancialNormalizer(BaseNormalizer):
    def normalize(self, raw):
        data = raw.raw_data

        return FinancialRecord(
            symbol=to_ts_code(data["code"]),
            metric_name="net_income",
            value=float(data["netProfit"]),
            event_time=datetime.strptime(data["statDate"], "%Y-%m-%d"),
            available_time=datetime.strptime(data["pubDate"], "%Y-%m-%d"),
            processing_time=raw.ingest_time,
            source=raw.source,
        )