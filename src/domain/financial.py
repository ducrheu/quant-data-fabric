from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class FinancialRecord(BaseModel):

    symbol: str

    metric_name:str

    value: float

    event_time: datetime

    available_time:datetime

    processing_time:datetime

    source: str

    revision_id: int = 1

class SaveOutcome(str, Enum):
    """ 一条记录落库的三种结果 """

    INSERTED = "inserted"   # 新事实的第一版
    RESTATED = "restated"   # 已有事实的新版本 （重述）
    DUPLICATE = "duplicate" # 与已有版本完全重复，跳过
