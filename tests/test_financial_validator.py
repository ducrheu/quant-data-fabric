from src.domain.raw import RawRecord
from src.validators.financial import validate_income_raw
from datetime import datetime

def test_validator_return_no_errors_for_good_data():
    raw = RawRecord(
        source = "tushare",
        raw_data={
            "ts_code": "600519.SH",
            "n_income": 80000000000,
            "end_date": "20251231",
            "ann_date": "20260430",
        },
        ingest_time = datetime(2026, 5, 1)
    )

    errors = validate_income_raw(raw)

    assert errors == []


def test_validator_collections_all_errors():
    raw = RawRecord(
        source="tushare",
        raw_data={
            "n_income": "abc",
            "end_date": "2025-12-31",
            "ann_date": "20260430",
        },
        ingest_time=datetime(2026, 5, 1),
    )

    errors = validate_income_raw(raw)

    assert "missing ts_code" in errors
    assert "invalid n_income" in errors
    assert "invalid end_date" in errors