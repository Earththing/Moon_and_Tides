import json
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("tideline")


def _tool(name: str, description: str, properties: dict, required: list[str]) -> Tool:
    return Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        _tool("geocode", "Geocode an address to lat/lon coordinates.",
              {"address": {"type": "string", "description": "Address or place name"}},
              ["address"]),

        _tool("find_stations", "Find NOAA tide stations near a location.",
              {
                  "lat": {"type": "number"},
                  "lon": {"type": "number"},
                  "max_results": {"type": "integer", "default": 5},
                  "max_radius_miles": {"type": "number", "default": 100.0},
              },
              ["lat", "lon"]),

        _tool("get_tides_day", "Get high/low tide predictions for a single day.",
              {
                  "station_id": {"type": "string"},
                  "date": {"type": "string", "description": "YYYY-MM-DD"},
              },
              ["station_id", "date"]),

        _tool("get_tides_range", "Get high/low tide predictions for a date range.",
              {
                  "station_id": {"type": "string"},
                  "begin_date": {"type": "string", "description": "YYYYMMDD"},
                  "end_date": {"type": "string", "description": "YYYYMMDD"},
              },
              ["station_id", "begin_date", "end_date"]),

        _tool("get_station_info", "Get full metadata for a NOAA tide station.",
              {"station_id": {"type": "string"}},
              ["station_id"]),

        _tool("get_tidal_type", "Get the tidal pattern type for a station.",
              {"station_id": {"type": "string"}},
              ["station_id"]),

        _tool("get_extreme_tides", "Find extreme high or low tides at a station.",
              {
                  "station_id": {"type": "string"},
                  "begin_date": {"type": "string"},
                  "end_date": {"type": "string"},
                  "percentile": {"type": "number", "default": 0.90},
              },
              ["station_id", "begin_date", "end_date"]),

        _tool("find_extreme_in_radius",
              "Highest high and lowest low tide at every station within a radius, "
              "ranked across stations. Dates: YYYY-MM-DD.",
              {
                  "lat": {"type": "number"},
                  "lon": {"type": "number"},
                  "radius_miles": {"type": "number"},
                  "begin_date": {"type": "string"},
                  "end_date": {"type": "string"},
              },
              ["lat", "lon", "radius_miles", "begin_date", "end_date"]),

        _tool("check_flood_risk", "Check flood risk at a station over a date range.",
              {
                  "station_id": {"type": "string"},
                  "begin_date": {"type": "string"},
                  "end_date": {"type": "string"},
              },
              ["station_id", "begin_date", "end_date"]),

        _tool("get_slack_water", "Find slack water times (tide reversal) for a date.",
              {
                  "station_id": {"type": "string"},
                  "date": {"type": "string", "description": "YYYY-MM-DD"},
              },
              ["station_id", "date"]),

        _tool("get_tidepooling_windows",
              "Find best tidepooling windows (low tide during daylight).",
              {
                  "station_id": {"type": "string"},
                  "begin_date": {"type": "string"},
                  "end_date": {"type": "string"},
                  "lat": {"type": "number"},
                  "lon": {"type": "number"},
              },
              ["station_id", "begin_date", "end_date", "lat", "lon"]),

        _tool("get_perigean_spring_tides",
              "Get Perigean spring tide dates for a year.",
              {"year": {"type": "integer"}},
              ["year"]),

        _tool("generate_ics_url",
              "Generate a calendar ICS download URL.",
              {
                  "lat": {"type": "number"},
                  "lon": {"type": "number"},
                  "year": {"type": "integer"},
                  "options": {"type": "string", "default": "hilo,alerts"},
                  "station_id": {"type": "string",
                                 "description": "Optional; overrides nearest-to-lat/lon"},
              },
              ["lat", "lon", "year"]),
    ]


def _ymd(d: str) -> str:
    """Accept YYYY-MM-DD or YYYYMMDD; return YYYYMMDD (what app/ expects)."""
    return d.replace("-", "")


def _text(data) -> list[TextContent]:
    if isinstance(data, (dict, list)):
        return [TextContent(type="text", text=json.dumps(data, indent=2))]
    return [TextContent(type="text", text=str(data))]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "geocode":
        from app.geocode import geocode_address
        return _text(geocode_address(arguments["address"]))

    elif name == "find_stations":
        from app.station_finder import find_nearest_stations
        return _text(find_nearest_stations(
            lat=arguments["lat"],
            lon=arguments["lon"],
            max_results=arguments.get("max_results", 5),
            max_radius_miles=arguments.get("max_radius_miles", 100.0),
        ))

    elif name == "get_tides_day":
        from app.tide_data import get_hilo_predictions
        d = datetime.strptime(arguments["date"], "%Y-%m-%d")
        begin = d.strftime("%Y%m%d")
        data = get_hilo_predictions(arguments["station_id"], begin, begin)
        return _text(data)

    elif name == "get_tides_range":
        from app.tide_data import get_hilo_predictions
        return _text(get_hilo_predictions(
            arguments["station_id"],
            _ymd(arguments["begin_date"]),
            _ymd(arguments["end_date"]),
        ))

    elif name == "get_station_info":
        from app.station_finder import get_all_stations, get_tidal_type
        from app.tide_data import get_station_tidal_range
        stations = get_all_stations()
        station = next((s for s in stations if s["id"] == arguments["station_id"]), None)
        if not station:
            return _text({"error": "Station not found"})
        try:
            tr = get_station_tidal_range(arguments["station_id"])
        except Exception:
            tr = {}
        try:
            tt = get_tidal_type(arguments["station_id"])
        except Exception:
            tt = {"type": "unknown"}
        return _text({**station, **tr, "tidal_type": tt["type"]})

    elif name == "get_tidal_type":
        from app.station_finder import get_tidal_type
        return _text(get_tidal_type(arguments["station_id"]))

    elif name == "get_extreme_tides":
        from app.tide_data import get_hilo_predictions
        data = get_hilo_predictions(
            arguments["station_id"],
            _ymd(arguments["begin_date"]),
            _ymd(arguments["end_date"]),
        )
        percentile = arguments.get("percentile", 0.90)
        highs = sorted([d for d in data if d["type"] == "H"], key=lambda x: x["height_ft"], reverse=True)
        lows = sorted([d for d in data if d["type"] == "L"], key=lambda x: x["height_ft"])
        n_high = max(1, int(len(highs) * (1 - percentile)))
        n_low = max(1, int(len(lows) * (1 - percentile)))
        return _text({"extreme_highs": highs[:n_high], "extreme_lows": lows[:n_low]})

    elif name == "find_extreme_in_radius":
        # Per station: the highest high and lowest low in the window, so both
        # "highest" and "lowest tide within N miles" are answerable.
        from concurrent.futures import ThreadPoolExecutor
        from app.station_finder import find_stations_in_radius
        from app.tide_data import get_hilo_predictions
        begin, end = _ymd(arguments["begin_date"]), _ymd(arguments["end_date"])
        stations = find_stations_in_radius(
            arguments["lat"], arguments["lon"], arguments["radius_miles"]
        )

        def extremes(s):
            try:
                data = get_hilo_predictions(s["id"], begin, end)
            except Exception:
                return []
            meta = {"station_id": s["id"], "station_name": s["name"],
                    "distance_miles": round(s["distance_miles"], 1)}
            out = []
            highs = [d for d in data if d["type"] == "H"]
            lows = [d for d in data if d["type"] == "L"]
            if highs:
                out.append({**max(highs, key=lambda d: d["height_ft"]), **meta})
            if lows:
                out.append({**min(lows, key=lambda d: d["height_ft"]), **meta})
            return out

        with ThreadPoolExecutor(max_workers=8) as pool:
            found = [e for batch in pool.map(extremes, stations) for e in batch]
        highs = sorted((e for e in found if e["type"] == "H"),
                       key=lambda e: e["height_ft"], reverse=True)
        lows = sorted((e for e in found if e["type"] == "L"), key=lambda e: e["height_ft"])
        return _text({
            "stations_checked": len(stations),
            "highest_highs": highs[:10],
            "lowest_lows": lows[:10],
        })

    elif name == "check_flood_risk":
        from app.alert_engine import _get_flood_levels, check_flood_risk
        station_id = arguments["station_id"]
        if _get_flood_levels(station_id) is None:
            return _text({"message": "No NOAA flood thresholds for this station."})
        return _text(check_flood_risk(
            station_id, _ymd(arguments["begin_date"]), _ymd(arguments["end_date"])))

    elif name == "get_slack_water":
        from app.special_events import get_slack_water
        date_str = datetime.strptime(arguments["date"], "%Y-%m-%d").strftime("%Y-%m-%d")
        return _text(get_slack_water(arguments["station_id"], date_str))

    elif name == "get_tidepooling_windows":
        from app.special_events import get_tidepooling_windows
        return _text(get_tidepooling_windows(
            arguments["station_id"],
            _ymd(arguments["begin_date"]),
            _ymd(arguments["end_date"]),
            arguments["lat"],
            arguments["lon"],
        ))

    elif name == "get_perigean_spring_tides":
        from app.special_events import get_perigean_spring_tides
        return _text(get_perigean_spring_tides(arguments["year"]))

    elif name == "generate_ics_url":
        lat = arguments["lat"]
        lon = arguments["lon"]
        year = arguments["year"]
        options = arguments.get("options", "hilo,alerts")
        if arguments.get("station_id"):
            url = (f"http://localhost:8000/calendar/{year}/station/"
                   f"{arguments['station_id']}.ics?options={options}")
        else:
            url = f"http://localhost:8000/calendar/{year}/{lat},{lon}.ics?options={options}"
        return _text({"url": url})

    else:
        return _text({"error": f"Unknown tool: {name}"})


async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    main()
