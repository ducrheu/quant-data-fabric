from datetime import datetime

from pydantic import BaseModel


class FactorRecord(BaseModel):
    symbol: str
    factor_name: str
    trade_time: datetime
    value: float