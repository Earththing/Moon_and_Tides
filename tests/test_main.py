import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_STATIONS = [
    {"id": "9414290", "name": "San Francisco", "lat": 37.8063, "lon": -122.4659,
     "state": "CA", "tidal": 1, "harmonic": 1},
]

MOCK_HILO = [
    {"date": "2026-06-21", "time": "03:15", "height_ft": 5.2, "type": "H"},
    {"date": "2026-06-21", "time": "09:30", "height_ft": 0.8, "type": "L"},
    {"date": "2026-06-21", "time": "15:45", "height_ft": 4.9, "type": "H"},
    {"date": "2026-06-21", "time": "21:00", "height_ft": 1.1, "type": "L"},
]

MOCK_GEOCODE = [{"lat": 37.7749, "lon": -122.4194, "display_name": "San Francisco, CA"}]


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    import app.tide_data as td
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")


def test_geocode_endpoint():
    with patch("app.geocode.geocode_address", return_value=MOCK_GEOCODE):
        resp = client.post("/geocode", json={"address": "San Francisco, CA"})
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["lat"] == 37.7749


def test_stations_nearest():
    with patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS):
        with patch("app.station_finder.get_tidal_type", return_value={"type": "mixed", "description": ""}):
            resp = client.get("/api/v1/stations/nearest?lat=37.7749&lon=-122.4194&count=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["id"] == "9414290"
    assert "tidal_type" in data[0]


def test_stations_radius():
    with patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS):
        resp = client.get("/api/v1/stations/radius?lat=37.7749&lon=-122.4194&radius_miles=50")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all("distance_miles" in s for s in data)


def test_station_detail():
    with patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS):
        with patch("app.station_finder.get_tidal_type", return_value={"type": "mixed", "description": ""}):
            with patch("app.tide_data.get_station_tidal_range",
                       return_value={"mean_range_ft": 4.0, "mean_high_ft": 5.0, "mean_low_ft": 1.0}):
                resp = client.get("/api/v1/station/9414290")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "9414290"
    assert "mean_range_ft" in data
    assert "has_flood_thresholds" in data


def test_station_not_found():
    with patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS):
        resp = client.get("/api/v1/station/9999999")
    assert resp.status_code == 404


def test_tides_day():
    with patch("app.tide_data.get_hilo_predictions", return_value=MOCK_HILO):
        with patch("app.tide_data.get_water_level_curve", return_value=[]):
            resp = client.get("/api/v1/tides/day?station_id=9414290&date=2026-06-21")
    assert resp.status_code == 200
    data = resp.json()
    assert "hilo" in data
    assert "curve" in data
    assert len(data["hilo"]) == 4


def test_tides_range():
    with patch("app.tide_data.get_hilo_predictions", return_value=MOCK_HILO):
        resp = client.get("/api/v1/tides/range?station_id=9414290&begin=2026-06-21&end=2026-06-21")
    assert resp.status_code == 200
    data = resp.json()
    assert "hilo" in data


def test_year_summary():
    # Build mock year data
    mock_year = []
    for mo in range(1, 13):
        for day in range(1, 29):
            mock_year.append({"date": f"2026-{mo:02d}-{day:02d}", "time": "06:00",
                              "height_ft": 5.0, "type": "H"})
            mock_year.append({"date": f"2026-{mo:02d}-{day:02d}", "time": "18:00",
                              "height_ft": 0.8, "type": "L"})
    with patch("app.tide_data.get_hilo_predictions", return_value=mock_year):
        resp = client.get("/api/v1/tides/year-summary?station_id=9414290&year=2026")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["monthly_mean_high"]) == 12
    assert len(data["monthly_mean_low"]) == 12


def test_special_events():
    resp = client.get("/api/v1/special-events?station_id=9414290&year=2026")
    assert resp.status_code == 200
    data = resp.json()
    assert "tidepooling_windows" in data
    assert "flood_risk" in data


def test_map_status_batch():
    with patch("app.tide_data.get_hilo_predictions", return_value=MOCK_HILO):
        resp = client.get("/api/v1/map/status?ids=9414290,9414750&date=2026-06-21")
    assert resp.status_code == 200
    data = resp.json()
    assert "stations" in data
    assert set(data["stations"].keys()) == {"9414290", "9414750"}
    for entry in data["stations"].values():
        assert len(entry["hilo"]) == 4
        # extremes/flood not requested — must not be present
        assert "high_threshold_ft" not in entry
        assert "has_flood" not in entry


def test_map_status_with_extremes():
    with patch("app.tide_data.get_hilo_predictions", return_value=MOCK_HILO):
        with patch("app.alert_engine.compute_extreme_thresholds",
                   return_value={"high_threshold_ft": 6.1, "low_threshold_ft": -0.5}):
            resp = client.get("/api/v1/map/status?ids=9414290&date=2026-06-21&extremes=true")
    assert resp.status_code == 200
    entry = resp.json()["stations"]["9414290"]
    assert entry["high_threshold_ft"] == 6.1
    assert entry["low_threshold_ft"] == -0.5


def test_map_status_skips_failing_station():
    def fail_for_bad(station_id, *a, **kw):
        if station_id == "0000000":
            raise ValueError("no data")
        return MOCK_HILO
    with patch("app.tide_data.get_hilo_predictions", side_effect=fail_for_bad):
        resp = client.get("/api/v1/map/status?ids=9414290,0000000&date=2026-06-21")
    assert resp.status_code == 200
    data = resp.json()["stations"]
    assert "9414290" in data
    assert "0000000" not in data


def test_calendar_ics_download():
    def mock_get_all(return_value=MOCK_STATIONS):
        return MOCK_STATIONS

    # Build year mock
    mock_year = []
    for mo in range(1, 13):
        for day in range(1, 29):
            mock_year.extend([
                {"date": f"2026-{mo:02d}-{day:02d}", "time": "03:15",
                 "height_ft": 5.2, "type": "H"},
                {"date": f"2026-{mo:02d}-{day:02d}", "time": "09:30",
                 "height_ft": 0.8, "type": "L"},
            ])

    with patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS):
        with patch("app.tide_data.get_hilo_predictions", return_value=mock_year):
            resp = client.get("/calendar/2026/37.7749,-122.4194.ics")
    assert resp.status_code == 200
    assert b"BEGIN:VCALENDAR" in resp.content
