import pytest

from src.universe import load_universe, save_universe, select_universe

def test_select_universe_is_order_independent():
    candidates = [f"{index:06d}.SZ" for index in range(1, 501)]

    first = select_universe(candidates, 300, 42)
    second = select_universe(list(reversed(candidates)), 300, 42)

    assert first == second
    assert len(first) == 300
    assert first == sorted(first)

def test_select_universe_reject_oversize():
    with pytest.raises(ValueError):
        select_universe(["000001.SZ", "000002.SZ"], 3, 1)

def test_save_and_load_snapshot(tmp_path):
    path = tmp_path / "universe.json"

    save_universe(
        symbols=["600519.SH", "000001.SZ"],
        as_of="20250102",
        seed=42,
        candidates=5400,
        path=str(path),
    )

    assert load_universe(str(path)) == {"600519.SH", "000001.SZ"}