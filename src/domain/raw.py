from datetime import datetime
from time import struct_time
from pydantic import BaseModel

class RawRecord(BaseModel):

    source: str

    raw_data: dict

    ingest_time: datetime
