from datetime import datetime
from pydantic import BaseModel

class PriceRecord(BaseModel):

    symbol: str

    trade_time: datetime

    open: float

    high: float

    low: float

    close: float

    volume: float

    source: str