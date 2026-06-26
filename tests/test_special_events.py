import pytest
from unittest.mock import patch, MagicMock

from app.special_events import (
    get_slack_water,
    get_tidepooling_windows,
    get_perigean_spring_tides,
    get_tidal_bore_times,
)


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    import app.tide_data as td
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")


def _make_sine_curve():
    """Simulate a tide curve with one high and one low."""
    import math
    records = []
    for i in range(240):  # 6-minute intervals = 24 hours
        t_hours = i * 6 / 60
        # 12.4-hour semidiurnal period
        height = 3.0 + 2.5 * math.sin(2 * math.pi * t_hours / 12.4)
        h = int(t_hours)
        m = int((t_hours - h) * 60)
        records.append({
            "date": "2026-06-21",
            "time": f"{h:02d}:{m:02d}",
            "height_ft": round(height, 3),
        })
    return records


def test_slack_water_finds_reversals():
    curve = _make_sine_curve()
    with patch("app.tide_data.get_water_level_curve", return_value=curve):
        slacks = get_slack_water("9414290", "2026-06-21")
    assert len(slacks) >= 1
    assert all("time" in s and "between" in s for s in slacks)
    assert all(s["between"] in ("high_to_low", "low_to_high") for s in slacks)


def test_slack_water_empty_curve():
    with patch("app.tide_data.get_water_level_curve", return_value=[]):
        slacks = get_slack_water("9414290", "2026-06-21")
    assert slacks == []


def test_tidepooling_windows():
    mock_hilo = []
    for day in range(1, 15):
        mock_hilo.extend([
            {"date": f"2026-07-{day:02d}", "time": "10:30",
             "height_ft": -0.2 if day <= 5 else 0.5, "type": "L"},
            {"date": f"2026-07-{day:02d}", "time": "22:30", "height_ft": 5.0, "type": "H"},
        ])

    with patch("app.tide_data.get_hilo_predictions", return_value=mock_hilo):
        windows = get_tidepooling_windows(
            "9414290", "20260701", "20260714", 37.7749, -122.4194
        )

    assert isinstance(windows, list)
    # All windows should have low tide during daylight
    for w in windows:
        assert "date" in w
        assert "low_tide_time" in w
        assert "score" in w
        assert "sunrise" in w
        assert "sunset" in w
    # Lowest tides should rank highest
    if len(windows) >= 2:
        assert windows[0]["score"] >= windows[1]["score"]


def test_perigean_spring_tides_2026():
    events = get_perigean_spring_tides(2026)
    assert isinstance(events, list)
    # There are typically 4-6 perigean spring tides per year
    assert 2 <= len(events) <= 8
    for e in events:
        assert "date" in e
        assert "moon_phase" in e
        assert e["moon_phase"] in ("new moon", "full moon")
        assert "perigee_distance_km" in e
        assert e["date"].startswith("2026")


def test_perigean_spring_tides_cached(tmp_path, monkeypatch):
    import app.tide_data as td
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")
    # First call computes
    events1 = get_perigean_spring_tides(2026)
    # Second call should use cache (no ephem re-computation)
    events2 = get_perigean_spring_tides(2026)
    assert events1 == events2


def test_tidal_bore_known_location():
    mock_hilo = [
        {"date": "2026-06-21", "time": "06:00", "height_ft": 25.0, "type": "H"},
        {"date": "2026-06-21", "time": "12:00", "height_ft": 2.0, "type": "L"},
    ]
    with patch("app.tide_data.get_hilo_predictions", return_value=mock_hilo):
        result = get_tidal_bore_times("turnagain_arm_ak", "2026-06-21")
    assert result is not None
    assert "bore_times" in result
    assert len(result["bore_times"]) >= 1
    # Bore arrives 2.5 hours after low tide (12:00 + 2:30 = 14:30)
    assert result["bore_times"][0]["bore_time"] == "14:30"


def test_tidal_bore_unknown_location():
    result = get_tidal_bore_times("portland_me", "2026-06-21")
    assert result is None
