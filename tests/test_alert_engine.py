import pytest
from unittest.mock import patch, MagicMock

from app.alert_engine import (
    compute_extreme_thresholds,
    find_extreme_tides,
    find_extreme_in_radius,
    check_flood_risk,
)


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    import app.tide_data as td
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")


def _make_year_data():
    data = []
    for mo in range(1, 13):
        for day in range(1, 29):
            # Make month 12 high tides extreme
            high = 7.5 if mo == 12 else 5.0 + mo * 0.05
            low = -0.5 if mo == 1 and day <= 5 else 0.5 + day * 0.01
            data.append({"date": f"2026-{mo:02d}-{day:02d}", "time": "03:00",
                         "height_ft": high, "type": "H"})
            data.append({"date": f"2026-{mo:02d}-{day:02d}", "time": "15:00",
                         "height_ft": low, "type": "L"})
    return data


MOCK_STATIONS = [
    {"id": "9414290", "name": "San Francisco", "lat": 37.8063, "lon": -122.4659,
     "state": "CA", "tidal": 1, "harmonic": 1, "distance_miles": 3.0},
]


def test_compute_extreme_thresholds():
    with patch("app.alert_engine.get_hilo_predictions", return_value=_make_year_data()):
        thresholds = compute_extreme_thresholds("9414290")
    assert "high_threshold_ft" in thresholds
    assert "low_threshold_ft" in thresholds
    assert thresholds["high_threshold_ft"] > 5.0


def test_find_extreme_tides():
    year_data = _make_year_data()
    with patch("app.alert_engine.get_hilo_predictions", return_value=year_data):
        # Use explicit thresholds so we don't need two API calls
        extremes = find_extreme_tides(
            "9414290", "20261201", "20261231",
            high_threshold_ft=7.0,
            low_threshold_ft=0.0,
        )
    # December high tides (7.5 ft) should all be extreme
    king_tides = [e for e in extremes if e["extreme_type"] == "king_tide"]
    assert len(king_tides) > 0
    assert all(e["height_ft"] >= 7.0 for e in king_tides)


def test_find_extreme_in_radius():
    year_data = _make_year_data()
    with patch("app.alert_engine.find_stations_in_radius", return_value=MOCK_STATIONS):
        with patch("app.alert_engine.get_hilo_predictions", return_value=year_data):
            with patch("app.alert_engine.compute_extreme_thresholds",
                       return_value={"high_threshold_ft": 7.0, "low_threshold_ft": 0.0}):
                results = find_extreme_in_radius(
                    37.7749, -122.4194, 50, "20261201", "20261231"
                )
    assert isinstance(results, list)
    if results:
        assert "station_id" in results[0]
        assert "distance_miles" in results[0]


def test_check_flood_risk_no_thresholds():
    # Without flood thresholds in DB (and NOAA returns no data), returns empty
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"self": None}  # NOAA returns null self when no thresholds
    with patch("httpx.get", return_value=mock_resp):
        results = check_flood_risk("9414290", "20260101", "20260131")
    assert results == []


def test_check_flood_risk_with_thresholds(tmp_path, monkeypatch):
    # The autouse clear_cache fixture already set CACHE_DB to tmp_path/tides.db
    # We use the same path so flood data and get_hilo both share the DB
    from app.tide_data import _db_conn
    with _db_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO flood_levels "
            "(station_id, minor_ft, moderate_ft, major_ft, fetched_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            ("9414290", 5.5, 6.0, 6.5)
        )

    high_data = [
        {"date": "2026-01-15", "time": "03:00", "height_ft": 5.8, "type": "H"},
        {"date": "2026-01-16", "time": "03:00", "height_ft": 5.0, "type": "H"},
        {"date": "2026-01-15", "time": "15:00", "height_ft": 0.5, "type": "L"},
    ]

    # Patch at the point of use (alert_engine imports get_hilo_predictions by name)
    with patch("app.alert_engine.get_hilo_predictions", return_value=high_data):
        results = check_flood_risk("9414290", "20260101", "20260131")

    assert len(results) >= 1
    assert results[0]["flood_level"] == "minor"
