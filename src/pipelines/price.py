from pydantic import BaseModel

from src.connectors.price_connector import TusharePriceConnector
from src.normalizers.price import TusharePriceNormalizer
from src.repositories.price import PriceRepository
from src.validators.price import validate_daily_raw, validate_price_record

class PriceIngestResult(BaseModel):
    total: int = 0
    saved: int = 0
    skipped: int = 0
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

            inserted = self.repository.save(record)
            if inserted:
                result.saved += 1
            else:
                result.skipped += 1

        return result

    def run_market(self, trade_date: str, symbols: set[str]) -> PriceIngestResult:
        """摄入某个交易日的全市场日线，只保留池内的票"""
        result = PriceIngestResult()
        raw_records = self.connector.fetch_daily_market(trade_date)
        kept = [
            raw for raw in raw_records
            if raw.raw_data.get("ts_code") in symbols
        ]
        result.total = len(kept)

        valid_records = []
        for index, raw in enumerate(kept):
            errors = validate_daily_raw(raw)
            if errors:
                result.failed += 1
                result.errors.append(
                    f"{trade_date} {raw.raw_data.get('ts_code')} (format): {errors}"
                )
                continue

            record = self.normalizer.normalize(raw)
            errors = validate_price_record(record)
            if errors:
                result.failed += 1
                result.errors.append(
                    f"{trade_date} {record.symbol} (business): {errors}"
                )
                continue

            valid_records.append(record)

        inserted = self.repository.save_many(valid_records)
        result.saved = inserted
        result.skipped = len(valid_records) - inserted

        return result
