import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    import app.tide_data as td
    monkeypatch.setattr(td, "CACHE_DB", tmp_path / "tides.db")


MOCK_STATIONS = [
    {"id": "9414290", "name": "San Francisco", "lat": 37.8063, "lon": -122.4659,
     "state": "CA", "tidal": 1, "harmonic": 1},
]

MOCK_HILO = [
    {"date": "2026-06-21", "time": "03:15", "height_ft": 5.2, "type": "H"},
    {"date": "2026-06-21", "time": "09:30", "height_ft": 0.8, "type": "L"},
]

MOCK_GEOCODE = [{"lat": 37.7749, "lon": -122.4194, "display_name": "San Francisco, CA"}]


@pytest.mark.asyncio
async def test_list_tools():
    from mcp_server import list_tools
    tools = await list_tools()
    tool_names = {t.name for t in tools}
    assert "geocode" in tool_names
    assert "find_stations" in tool_names
    assert "get_tides_day" in tool_names
    assert "get_tides_range" in tool_names
    assert "get_station_info" in tool_names
    assert "get_tidal_type" in tool_names
    assert "get_extreme_tides" in tool_names
    assert "find_extreme_in_radius" in tool_names
    assert "check_flood_risk" in tool_names
    assert "get_slack_water" in tool_names
    assert "get_tidepooling_windows" in tool_names
    assert "get_perigean_spring_tides" in tool_names
    assert "generate_ics_url" in tool_names


@pytest.mark.asyncio
async def test_geocode_tool():
    from mcp_server import call_tool
    with patch("app.geocode.geocode_address", return_value=MOCK_GEOCODE):
        result = await call_tool("geocode", {"address": "San Francisco, CA"})
    data = json.loads(result[0].text)
    assert data[0]["lat"] == 37.7749


@pytest.mark.asyncio
async def test_find_stations_tool():
    from mcp_server import call_tool
    with patch("app.station_finder.get_all_stations", return_value=MOCK_STATIONS):
        result = await call_tool("find_stations", {"lat": 37.7749, "lon": -122.4194})
    data = json.loads(result[0].text)
    assert isinstance(data, list)
    assert data[0]["id"] == "9414290"


@pytest.mark.asyncio
async def test_get_tides_day_tool():
    from mcp_server import call_tool
    with patch("app.tide_data.get_hilo_predictions", return_value=MOCK_HILO):
        result = await call_tool("get_tides_day", {"station_id": "9414290", "date": "2026-06-21"})
    data = json.loads(result[0].text)
    assert isinstance(data, list)
    assert all("height_ft" in item for item in data)


@pytest.mark.asyncio
async def test_get_tides_range_tool():
    from mcp_server import call_tool
    with patch("app.tide_data.get_hilo_predictions", return_value=MOCK_HILO):
        result = await call_tool("get_tides_range", {
            "station_id": "9414290", "begin_date": "20260621", "end_date": "20260621"
        })
    data = json.loads(result[0].text)
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_generate_ics_url_tool():
    from mcp_server import call_tool
    result = await call_tool("generate_ics_url", {"lat": 37.7749, "lon": -122.4194, "year": 2026})
    data = json.loads(result[0].text)
    assert "url" in data
    assert "2026" in data["url"]
    assert "37.7749" in data["url"]


@pytest.mark.asyncio
async def test_get_extreme_tides_tool():
    from mcp_server import call_tool
    # Need at least some data to have extremes
    year_data = [
        {"date": f"2026-01-{d:02d}", "time": "06:00", "height_ft": 4.5 + d * 0.1, "type": "H"}
        for d in range(1, 31)
    ] + [
        {"date": f"2026-01-{d:02d}", "time": "18:00", "height_ft": 0.5 + d * 0.02, "type": "L"}
        for d in range(1, 31)
    ]
    with patch("app.tide_data.get_hilo_predictions", return_value=year_data):
        result = await call_tool("get_extreme_tides", {
            "station_id": "9414290", "begin_date": "20260101", "end_date": "20260131"
        })
    data = json.loads(result[0].text)
    assert "extreme_highs" in data
    assert "extreme_lows" in data
