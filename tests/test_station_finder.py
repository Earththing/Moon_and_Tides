import json
import pytest
from unittest.mock import patch, MagicMock

from app.station_finder import (
    find_nearest_stations,
    find_stations_in_radius,
    haversine_miles,
    get_all_stations,
)


# Minimal NOAA MDAPI station response
MOCK_STATIONS_RESPONSE = {
    "stations": [
        {"id": "9414290", "name": "San Francisco", "lat": "37.8063", "lng": "-122.4659",
         "state": "CA", "tidal": True, "greatlakes": False},
        {"id": "9414750", "name": "Alameda", "lat": "37.7717", "lng": "-122.3000",
         "state": "CA", "tidal": True, "greatlakes": False},
        {"id": "9415020", "name": "Point Reyes", "lat": "37.9956", "lng": "-122.9758",
         "state": "CA", "tidal": True, "greatlakes": False},
        {"id": "9419750", "name": "Crescent City", "lat": "41.7450", "lng": "-124.1817",
         "state": "CA", "tidal": True, "greatlakes": False},
        {"id": "8518750", "name": "The Battery", "lat": "40.6996", "lng": "-74.0166",
         "state": "NY", "tidal": True, "greatlakes": False},
    ]
}


def _make_mock_response(data: dict):
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    import app.tide_data as td
    import app.station_finder as sf
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")


def test_nearest_to_sf():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)):
        stations = find_nearest_stations(37.7749, -122.4194, max_results=1)
    assert stations[0]["id"] == "9414290"


def test_radius_bounds():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)):
        stations = find_stations_in_radius(37.7749, -122.4194, 50)
    assert len(stations) >= 3
    assert all(s["distance_miles"] <= 50 for s in stations)


def test_haversine_sf_to_la():
    # SF to LA is ~347 miles
    dist = haversine_miles(37.7749, -122.4194, 34.0522, -118.2437)
    assert 330 < dist < 370


def test_haversine_zero():
    dist = haversine_miles(37.0, -122.0, 37.0, -122.0)
    assert dist == 0.0


def test_nearest_returns_sorted():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)):
        stations = find_nearest_stations(37.7749, -122.4194, max_results=3)
    dists = [s["distance_miles"] for s in stations]
    assert dists == sorted(dists)


def test_radius_excludes_distant():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)):
        stations = find_stations_in_radius(37.7749, -122.4194, 50)
    ids = [s["id"] for s in stations]
    assert "8518750" not in ids  # NY station is thousands of miles away
