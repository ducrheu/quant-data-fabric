from src.trading_calendar import load_trading_days, to_date, save_trading_days

def test_to_date_parses_tushare_format():
    assert to_date("20250102").isoformat() == "2025-01-02"

def test_save_and_load_trading_days(tmp_path):
    path = tmp_path / "trading_days.json"

    save_trading_days(
        days=["20250103", "20250102", "20250102"],
        start="20250102",
        end="20250103",
        source="test",
        path=str(path),
    )
    assert load_trading_days(str(path)) == ["20250102", "20250103"]