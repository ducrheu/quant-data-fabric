from pydantic import BaseModel

from src.connectors.price_connector import TusharePriceConnector
from src.normalizers.price import TusharePriceNormalizer
from src.repositories.price import PriceRepository
from src.validators.price import validate_daily_raw, validate_price_record

class PriceIngestResult(BaseModel):
    total: int = 0
    saved: int = 0
    failed: int = 0
    errors: list[str] = []

class PricePipeline:
    def __init__(
            self,
            connector: TusharePriceConnector,
            normalizer: TusharePriceNormalizer,
            repository: PriceRepository,
    ):
        self.connector = connector
        self.normalizer = normalizer
        self.repository = repository

    def run(self, ts_code: str, start_date: str, end_date: str) -> PriceIngestResult:
        result = PriceIngestResult()

        raw_records = self.connector.fetch_daily(
            ts_code = ts_code,
            start_date = start_date,
            end_date = end_date,
        )
        result.total = len(raw_records)

        for index, raw in enumerate(raw_records):
            errors = validate_daily_raw(raw)
            if errors:
                result.failed += 1
                result.errors.append(f"row {index} (format): {errors}")
                continue

            record = self.normalizer.normalize(raw)

            errors = validate_price_record(record)
            if errors:
                result.failed += 1
                result.errors.append(f"row {index} (business): {errors}")
                continue

            self.repository.save(record)
            result.saved += 1

        return result
