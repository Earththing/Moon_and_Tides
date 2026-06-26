import json
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from app.tide_data import _db_conn

NOAA_MDAPI = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"
APP_HEADER = "moon_and_tides/0.1"
STATION_CACHE_DAYS = 30  # NOAA station list changes infrequently


def _get_cached_stations() -> list[dict] | None:
    with _db_conn() as conn:
        rows = conn.execute(
            "SELECT json_data, fetched_at FROM stations LIMIT 1"
        ).fetchone()
        if rows is None:
            return None
        _, fetched_at_str = rows
        fetched_at = datetime.fromisoformat(fetched_at_str)
        if datetime.utcnow() - fetched_at > timedelta(days=STATION_CACHE_DAYS):
            return None
        all_rows = conn.execute("SELECT json_data FROM stations").fetchall()
    return [json.loads(r[0]) for r in all_rows]


def get_all_stations() -> list[dict]:
    cached = _get_cached_stations()
    if cached is not None:
        return cached

    url = f"{NOAA_MDAPI}/stations.json"
    params = {"type": "waterlevels", "application": APP_HEADER}
    resp = httpx.get(url, params=params, timeout=60)
    resp.raise_for_status()
    body = resp.json()

    stations = []
    now = datetime.utcnow().isoformat()
    with _db_conn() as conn:
        conn.execute("DELETE FROM stations")
        for s in body.get("stations", []):
            station = {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "lat": float(s.get("lat", 0)),
                "lon": float(s.get("lng", 0)),
                "state": s.get("state", ""),
                "tidal": 1 if s.get("tidal") else 0,
                "harmonic": 1 if s.get("greatlakes") is False and s.get("tidal") else 0,
            }
            # harmonic: stations with tidal predictions are harmonic
            # The NOAA API doesn't directly expose "harmonic" — use tidal flag as proxy
            station["harmonic"] = station["tidal"]
            stations.append(station)
            conn.execute(
                "INSERT OR REPLACE INTO stations "
                "(id, name, lat, lon, state, tidal, harmonic, json_data, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (station["id"], station["name"], station["lat"], station["lon"],
                 station["state"], station["tidal"], station["harmonic"],
                 json.dumps(station), now)
            )
    return stations


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest_stations(
    lat: float,
    lon: float,
    max_results: int = 5,
    max_radius_miles: float = 100.0,
    require_harmonic: bool = False,
) -> list[dict]:
    stations = get_all_stations()
    results = []
    for s in stations:
        if require_harmonic and not s.get("harmonic"):
            continue
        dist = haversine_miles(lat, lon, s["lat"], s["lon"])
        if dist <= max_radius_miles:
            results.append({**s, "distance_miles": dist})
    results.sort(key=lambda x: x["distance_miles"])
    return results[:max_results]


def find_stations_in_radius(lat: float, lon: float, radius_miles: float) -> list[dict]:
    stations = get_all_stations()
    results = []
    for s in stations:
        dist = haversine_miles(lat, lon, s["lat"], s["lon"])
        if dist <= radius_miles:
            results.append({**s, "distance_miles": dist})
    results.sort(key=lambda x: x["distance_miles"])
    return results


def get_tidal_type(station_id: str) -> dict:
    from app.tide_data import get_hilo_predictions
    from datetime import datetime, timedelta

    today = datetime.utcnow()
    begin = (today - timedelta(days=30)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    try:
        data = get_hilo_predictions(station_id, begin, end)
    except Exception:
        return {"type": "unknown", "description": "Could not determine tidal type."}

    if not data:
        return {"type": "unknown", "description": "No data available."}

    # Group by date and count tides per day
    by_date: dict[str, list[dict]] = {}
    for item in data:
        by_date.setdefault(item["date"], []).append(item)

    daily_counts = [len(v) for v in by_date.values()]
    if not daily_counts:
        return {"type": "unknown", "description": "No data available."}

    avg_tides = sum(daily_counts) / len(daily_counts)

    if avg_tides < 1.5:
        return {
            "type": "diurnal",
            "description": "This station experiences one high and one low tide per day (diurnal pattern).",
        }
    elif avg_tides > 1.8:
        # Check if heights are similar (semidiurnal) or mixed
        highs_by_day = {
            date: [i["height_ft"] for i in items if i["type"] == "H"]
            for date, items in by_date.items()
        }
        mixed_days = 0
        total_days = 0
        for date, highs in highs_by_day.items():
            if len(highs) >= 2:
                total_days += 1
                if abs(highs[0] - highs[1]) > 0.5:
                    mixed_days += 1
        if total_days > 0 and mixed_days / total_days > 0.4:
            return {
                "type": "mixed",
                "description": "This station has a mixed semidiurnal pattern: two unequal high tides per day.",
            }
        return {
            "type": "semidiurnal",
            "description": "This station experiences two nearly equal high and low tides per day.",
        }
    else:
        return {
            "type": "mixed",
            "description": "This station has a mixed tidal pattern.",
        }
