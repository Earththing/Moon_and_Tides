import pytest
from unittest.mock import patch, MagicMock
import json

from app.tide_data import get_hilo_predictions


MOCK_HILO_RESPONSE = {
    "predictions": [
        {"t": f"2026-01-{d:02d} {h:02d}:{m:02d}", "v": str(v), "type": t}
        for d in range(1, 32)
        for (h, m, v, t) in [
            (3, 15, 5.2, "H"),
            (9, 30, 0.8, "L"),
            (15, 45, 4.9, "H"),
            (21, 0, 1.1, "L"),
        ]
    ]
}

# Full year mock data for height tests
MOCK_YEAR_RESPONSE = {
    "predictions": [
        {"t": f"2026-{mo:02d}-{d:02d} 06:00", "v": str(4.5 + mo * 0.1), "type": "H"}
        for mo in range(1, 13)
        for d in range(1, 28)
    ] + [
        {"t": f"2026-{mo:02d}-{d:02d} 18:00", "v": str(0.5 + mo * 0.05), "type": "L"}
        for mo in range(1, 13)
        for d in range(1, 28)
    ]
}


def _make_mock_response(data: dict):
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    """Use a temp cache DB for each test."""
    import app.tide_data as td
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")


def test_hilo_returns_valid_structure():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_HILO_RESPONSE)):
        data = get_hilo_predictions("9414290", "20260101", "20260131")
    assert len(data) > 50
    assert all("height_ft" in d and "type" in d for d in data)
    assert all(d["type"] in ("H", "L") for d in data)


def test_hilo_alternates():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_HILO_RESPONSE)):
        data = get_hilo_predictions("9414290", "20260101", "20260131")
    types = [d["type"] for d in data]
    for i in range(len(types) - 1):
        assert types[i] != types[i + 1], f"Types not alternating at index {i}: {types[i-1:i+3]}"


def test_caching_returns_same_data():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_HILO_RESPONSE)) as mock_get:
        a = get_hilo_predictions("9414290", "20260101", "20260131")
        b = get_hilo_predictions("9414290", "20260101", "20260131")
    assert a == b
    # Second call should use cache — httpx.get called only once (per year)
    assert mock_get.call_count == 1


def test_height_values_plausible():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_YEAR_RESPONSE)):
        data = get_hilo_predictions("9414290", "20260101", "20261231")
    highs = [d["height_ft"] for d in data if d["type"] == "H"]
    lows = [d["height_ft"] for d in data if d["type"] == "L"]
    assert min(lows) > -2.0 and max(highs) < 8.0
