from pydantic import BaseModel
from src.connectors.tushare_connector import TushareConnector
from src.domain.raw import RawRecord
from src.normalizers.financial import TushareFinancialNormalizer
from src.repositories.financial import FinancialRepository
from src.validators.financial import validate_income_raw

class IngestResult(BaseModel):
    total: int = 0
    saved: int = 0
    failed: int = 0
    errors: list[str] = []

class FinancialPipeline:
    def __init__(
        self,
        connector: TushareConnector,
        normalizer: TushareFinancialNormalizer,
        repository: FinancialRepository,
    ):
        self.connector = connector
        self.normalizer = normalizer
        self.repository = repository

    def run(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> IngestResult:
        result = IngestResult()

        raw_records = self.connector.fetch_income(
            ts_code = ts_code,
            start_date = start_date,
            end_date = end_date,
        )
        result.total = len(raw_records)

        for index, raw in enumerate(raw_records):
            errors = validate_income_raw(raw)

            if errors:
                result.failed += 1
                result.errors.append(f"row {index}: {errors}")
                continue

            record = self.normalizer.normalize(raw)
            self.repository.save(record)
            result.saved += 1

        return result