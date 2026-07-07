import json
import pytest
from unittest.mock import patch, MagicMock

from app.station_finder import (
    find_nearest_stations,
    find_stations_in_radius,
    haversine_miles,
    get_all_stations,
    is_subordinate_station,
)


# Minimal NOAA MDAPI tidepredictions station response
# type "R" = reference (harmonic), "S" = subordinate (corrected hilo only)
MOCK_STATIONS_RESPONSE = {
    "stations": [
        {"id": "9414290", "name": "San Francisco", "lat": "37.8063", "lng": "-122.4659",
         "state": "CA", "type": "R", "reference_id": ""},
        {"id": "9414750", "name": "Alameda", "lat": "37.7717", "lng": "-122.3000",
         "state": "CA", "type": "R", "reference_id": ""},
        {"id": "9415020", "name": "Point Reyes", "lat": "37.9956", "lng": "-122.9758",
         "state": "CA", "type": "R", "reference_id": ""},
        {"id": "9419750", "name": "Crescent City", "lat": "41.7450", "lng": "-124.1817",
         "state": "CA", "type": "R", "reference_id": ""},
        {"id": "8518750", "name": "The Battery", "lat": "40.6996", "lng": "-74.0166",
         "state": "NY", "type": "R", "reference_id": ""},
        {"id": "9447427", "name": "Edmonds", "lat": "47.8133", "lng": "-122.383",
         "state": "WA", "type": "S", "reference_id": "9447130"},
        {"id": "9447130", "name": "Seattle", "lat": "47.6026", "lng": "-122.3393",
         "state": "WA", "type": "R", "reference_id": ""},
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


def test_subordinate_station_included_and_flagged():
    """Subordinate prediction stations (Edmonds) are discoverable, non-harmonic,
    and carry their reference station id."""
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)):
        stations = get_all_stations()
    edmonds = next(s for s in stations if s["id"] == "9447427")
    assert edmonds["station_type"] == "S"
    assert edmonds["harmonic"] == 0
    assert edmonds["reference_id"] == "9447130"
    seattle = next(s for s in stations if s["id"] == "9447130")
    assert seattle["station_type"] == "R"
    assert seattle["harmonic"] == 1


def test_nearest_to_edmonds_is_edmonds():
    """Searching Edmonds WA must resolve to the Edmonds subordinate station,
    not Seattle 14 miles away."""
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)):
        stations = find_nearest_stations(47.8107, -122.3774, max_results=2)
    assert stations[0]["id"] == "9447427"
    assert stations[0]["distance_miles"] < 1.0


def test_is_subordinate_station():
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)):
        assert is_subordinate_station("9447427") is True
        assert is_subordinate_station("9447130") is False
        assert is_subordinate_station("0000000") is False


def test_old_waterlevels_cache_invalidated():
    """Caches written before the tidepredictions switch (rows without a
    station_type key) must be treated as stale and refetched."""
    from app.tide_data import _db_conn
    with _db_conn() as conn:
        conn.execute(
            "INSERT INTO stations (id, name, lat, lon, state, tidal, harmonic, json_data, fetched_at) "
            "VALUES ('9414290', 'San Francisco', 37.8, -122.4, 'CA', 1, 1, ?, datetime('now'))",
            (json.dumps({"id": "9414290", "name": "San Francisco"}),)
        )
    with patch("httpx.get", return_value=_make_mock_response(MOCK_STATIONS_RESPONSE)) as mock_get:
        stations = get_all_stations()
    mock_get.assert_called_once()  # refetched despite fresh timestamp
    assert any(s["id"] == "9447427" for s in stations)
