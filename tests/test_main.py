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
                       return_value={"mean_range_ft": 4.0, "mean_high_ft": 5.0, "mean_low_ft": 1.0}), \
                 patch("app.alert_engine._get_flood_levels",
                       return_value={"minor_ft": 7.9, "moderate_ft": 8.5, "major_ft": 9.3}):
                resp = client.get("/api/v1/station/9414290")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "9414290"
    assert "mean_range_ft" in data
    # Flood thresholds are fetched on demand, not only read from a warm cache
    assert data["has_flood_thresholds"] is True
    assert data["flood_minor_ft"] == 7.9


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


def _special_events_patches(extremes_mock):
    # Previously this test ran unmocked and silently hit live NOAA (every
    # failure is swallowed by the route), so it asserted nothing real.
    return (
        patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS),
        patch("app.alert_engine.find_extreme_tides", extremes_mock),
        patch("app.alert_engine.check_flood_risk", return_value=[]),
        patch("app.special_events.get_tidepooling_windows", return_value=[]),
    )


def test_special_events():
    extremes = MagicMock(return_value=[])
    p1, p2, p3, p4 = _special_events_patches(extremes)
    with p1, p2, p3, p4:
        resp = client.get("/api/v1/special-events?station_id=9414290&year=2026")
    assert resp.status_code == 200
    data = resp.json()
    assert "tidepooling_windows" in data
    assert "flood_risk" in data
    assert extremes.called


def test_special_events_window_crosses_new_year():
    """In late December the feed must look into January, with each calendar
    year scanned separately (each year has its own king-tide threshold)."""
    from datetime import datetime as real_dt

    class FakeDatetime(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 12, 20, 18, 0, tzinfo=tz)

    extremes = MagicMock(return_value=[])
    p1, p2, p3, p4 = _special_events_patches(extremes)
    with p1, p2, p3, p4, patch("app.main.datetime", FakeDatetime):
        resp = client.get("/api/v1/special-events?station_id=9414290&year=2026")
    assert resp.status_code == 200
    windows = [c.args[1:3] for c in extremes.call_args_list]
    assert windows == [("20261220", "20261231"), ("20270101", "20270218")]
    # Perigean events come from both years and stay inside the window
    for e in resp.json()["perigean_spring_tides"]:
        assert "2026-12-20" <= e["date"] <= "2027-02-18"


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


def test_calendar_alerts_route_not_shadowed():
    """'/{lat_lon}.ics' also matches '...-alerts.ics'; the alerts route must win."""
    with patch("app.station_finder.find_nearest_stations", return_value=[{"id": "9414290"}]), \
         patch("app.ics_builder.build_alerts_only_ics", return_value=(b"ALERTS", {})) as alerts, \
         patch("app.ics_builder.build_tidal_ics", return_value=(b"FULL", {})):
        resp = client.get("/calendar/2026/37.7749,-122.4194-alerts.ics")
    assert resp.status_code == 200
    assert resp.content == b"ALERTS"
    assert alerts.call_args.args[:2] == ("9414290", 2026)


def test_calendar_station_route_uses_given_station():
    """The dashboard downloads by station ID, not nearest-to-coordinates."""
    stations = MOCK_STATIONS + [{"id": "9447427", "name": "Edmonds", "lat": 47.8133,
                                 "lon": -122.383, "state": "WA", "tidal": 1, "harmonic": 0}]
    with patch("app.station_finder.get_all_stations", return_value=stations), \
         patch("app.ics_builder.build_tidal_ics", return_value=(b"FULL", {})) as full, \
         patch("app.ics_builder.build_alerts_only_ics", return_value=(b"ALERTS", {})) as alerts:
        r1 = client.get("/calendar/2026/station/9447427.ics?options=hilo,radius&radius_miles=40")
        r2 = client.get("/calendar/2026/station/9447427-alerts.ics")
        r3 = client.get("/calendar/2026/station/0000000.ics")
    assert r1.status_code == 200 and r1.content == b"FULL"
    assert full.call_args.args[:3] == ("9447427", 2026, {"hilo": True, "radius": True})
    assert full.call_args.kwargs["radius_miles"] == 40
    assert r2.status_code == 200 and alerts.call_args.args[:2] == ("9447427", 2026)
    assert r3.status_code == 404


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

    # Patch where the name is looked up. ics_builder and alert_engine bind
    # get_hilo_predictions at import, so patching only app.tide_data missed
    # whenever they were imported first and the test silently hit live NOAA.
    with patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS), \
         patch("app.ics_builder.get_hilo_predictions", return_value=mock_year), \
         patch("app.alert_engine.get_hilo_predictions", return_value=mock_year):
        resp = client.get("/calendar/2026/37.7749,-122.4194.ics")
    assert resp.status_code == 200
    assert b"BEGIN:VCALENDAR" in resp.content
