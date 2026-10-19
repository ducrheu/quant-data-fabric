import json
from pydantic import BaseModel

from src.domain.financial import SaveOutcome
from src.repositories.ingest_batch import IngestBatchRepository
from src.validators.financial import validate_income_raw


class IngestResult(BaseModel):
    total: int = 0
    saved: int = 0
    restated: int = 0
    skipped: int = 0
    failed: int = 0
    batch_id: int | None = None
    errors: list[str] = []


class FinancialPipeline:
    """财务摄入流水线：取数 → 校验 → 映射 → 落库。

    参数形状**由 connector 的 fetch() 定义**，流水线只按顺序转发并计数。
    这样 Tushare（日频区间）和 baostock（季频单点）共用同一份逻辑。
    """

    def __init__(
        self,
        connector,
        normalizer,
        repository,
        batch_repository: IngestBatchRepository | None = None,
        validator=None,
        source: str = "tushare",
        api_name: str = "income",
    ):
        self.connector = connector
        self.normalizer = normalizer
        self.repository = repository
        self.batch_repository = batch_repository
        self.validator = validator or validate_income_raw
        self.source = source
        self.api_name = api_name

    def run(self, **params) -> IngestResult:
        result = IngestResult()

        if self.batch_repository is not None:
            result.batch_id = self.batch_repository.start(
                self.source,
                self.api_name,
                json.dumps(params, ensure_ascii=False, default=str),
            )

        raw_records = self.connector.fetch(**params)
        result.total = len(raw_records)

        for index, raw in enumerate(raw_records):
            errors = self.validator(raw)

            if errors:
                result.failed += 1
                result.errors.append(f"row {index}: {errors}")
                continue

            record = self.normalizer.normalize(raw)
            outcome = self.repository.save(record, result.batch_id)

            if outcome == SaveOutcome.DUPLICATE:
                result.skipped += 1
            else:
                result.saved += 1
                if outcome == SaveOutcome.RESTATED:
                    result.restated += 1

        if self.batch_repository is not None:
            status = "success" if result.failed == 0 else "partial"
            self.batch_repository.finish(
                result.batch_id,
                status,
                total=result.total,
                saved=result.saved,
                restated=result.restated,
                skipped=result.skipped,
                failed=result.failed,
            )

        return result
