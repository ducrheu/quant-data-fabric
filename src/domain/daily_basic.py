from datetime import datetime

from pydantic import BaseModel

class DailyBasicRecord(BaseModel):
    """每日基础指标，市值、换手、估值。用于因子中性化"""

    symbol: str
    trade_time: datetime
    close: float | None = None
    turnover_rate: float | None = None
    total_mv: float | None = None
    circ_mv: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    source: str
