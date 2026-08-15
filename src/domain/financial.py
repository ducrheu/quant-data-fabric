from datetime import datetime
from pydantic import BaseModel

class FinancialRecord(BaseModel):

    symbol: str

    metric_name:str

    value: float

    event_time: datetime

    available_time:datetime

    processing_time:datetime

    source: str

    revision_id: int = 1