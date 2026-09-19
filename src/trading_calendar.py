"""交易日历快照。

交易日清单是静态参考数据：一年只变一次，但每次跑摄入都要用。
来源是上证指数日线（指数不会停牌，一次调用即完整日历）；
trade_cal 在本账号档位限频 1次/分钟~1次/小时，不可用。
所以脚本永远只读快照文件，不碰接口。
"""

import json

from datetime import datetime, date
from pathlib import Path

TRADING_CALENDAR_PATH = "data/trading_days.json"

def to_date(trade_date: str) -> date:
    return datetime.strptime(trade_date, "%Y%m%d").date()

def save_trading_days(days, start, end, source, path=TRADING_CALENDAR_PATH):
    cleaned = sorted(set(days))
    payload = {
        "start": start,
        "end": end,
        "count": len(cleaned),
        "source": source,
        "days": cleaned,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cleaned

def load_trading_days(path=TRADING_CALENDAR_PATH) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload["days"]