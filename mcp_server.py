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
              "Find extreme tides at any station within a radius.",
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
              },
              ["lat", "lon", "year"]),
    ]


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
            arguments["begin_date"],
            arguments["end_date"],
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
            arguments["begin_date"],
            arguments["end_date"],
        )
        percentile = arguments.get("percentile", 0.90)
        highs = sorted([d for d in data if d["type"] == "H"], key=lambda x: x["height_ft"], reverse=True)
        lows = sorted([d for d in data if d["type"] == "L"], key=lambda x: x["height_ft"])
        n_high = max(1, int(len(highs) * (1 - percentile)))
        n_low = max(1, int(len(lows) * (1 - percentile)))
        return _text({"extreme_highs": highs[:n_high], "extreme_lows": lows[:n_low]})

    elif name == "find_extreme_in_radius":
        from app.station_finder import find_stations_in_radius
        from app.tide_data import get_hilo_predictions
        stations = find_stations_in_radius(
            arguments["lat"], arguments["lon"], arguments["radius_miles"]
        )
        results = []
        for s in stations[:10]:
            try:
                data = get_hilo_predictions(s["id"], arguments["begin_date"], arguments["end_date"])
                highs = sorted([d for d in data if d["type"] == "H"], key=lambda x: x["height_ft"], reverse=True)
                if highs:
                    top = highs[0]
                    results.append({**top, "station_id": s["id"], "station_name": s["name"],
                                    "distance_miles": s["distance_miles"]})
            except Exception:
                continue
        results.sort(key=lambda x: x["height_ft"], reverse=True)
        return _text(results)

    elif name == "check_flood_risk":
        from app.tide_data import get_hilo_predictions, _db_conn
        station_id = arguments["station_id"]
        with _db_conn() as conn:
            flood = conn.execute(
                "SELECT minor_ft FROM flood_levels WHERE station_id=?", (station_id,)
            ).fetchone()
        if not flood:
            return _text({"message": "No NOAA flood thresholds for this station."})
        minor_ft = flood[0]
        data = get_hilo_predictions(station_id, arguments["begin_date"], arguments["end_date"])
        risks = [
            {**d, "flood_level": "minor" if d["height_ft"] >= minor_ft else None}
            for d in data if d["type"] == "H" and d["height_ft"] >= minor_ft
        ]
        return _text(risks)

    elif name == "get_slack_water":
        # Requires curve data; return placeholder
        return _text({"message": "Slack water computation requires Phase 4 special_events module."})

    elif name == "get_tidepooling_windows":
        return _text({"message": "Tidepooling windows implemented in Phase 4."})

    elif name == "get_perigean_spring_tides":
        return _text({"message": "Perigean spring tides implemented in Phase 4."})

    elif name == "generate_ics_url":
        lat = arguments["lat"]
        lon = arguments["lon"]
        year = arguments["year"]
        options = arguments.get("options", "hilo,alerts")
        url = f"http://localhost:8000/calendar/{year}/{lat},{lon}.ics?options={options}"
        return _text({"url": url})

    else:
        return _text({"error": f"Unknown tool: {name}"})


def main():
    import asyncio
    asyncio.run(stdio_server(server))


if __name__ == "__main__":
    main()
