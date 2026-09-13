"""Factor pipeline: compute momentum factors from stored price data."""

from datetime import datetime

from pydantic import BaseModel

from src.factors.momentum import compute_momentum
from src.repositories.factor import FactorRepository
from src.repositories.price import PriceRepository

EARLIEST_HISTORY = datetime(1990, 1, 1)

class FactorResult(BaseModel):
    total: int = 0
    saved: int = 0
    skipped: int = 0

class MomentumFactorPipeline:
    def __init__(
            self,
            price_repository: PriceRepository,
            factor_repository: FactorRepository,
    ):
        self.price_repository = price_repository
        self.factor_repository = factor_repository

    def run(
            self,
            symbol: str,
            start_time: datetime,
            end_time: datetime,
            window: int,
    ) -> FactorResult:
        result = FactorResult()

        bars = self.price_repository.get_range(symbol, EARLIEST_HISTORY, end_time)
        factors = compute_momentum(bars, window)

        for record in factors:
            if record.trade_time < start_time:
                continue

            result.total += 1

            inserted = self.factor_repository.save(record)
            if inserted:
                result.saved += 1
            else:
                result.skipped += 1

        return result