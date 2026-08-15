from datetime import datetime
from src.domain.financial import FinancialRecord

record = FinancialRecord(

    symbol = "600519.SH",

    metric_name = "net_income",

    value = 80000000000,

    event_time = datetime(2025, 12, 31),

    available_time = datetime(2025, 4, 30),

    processing_time = datetime(2025, 5, 1),

    source = "tushare"

)

print(record)