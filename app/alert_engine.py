import json
from datetime import datetime

import httpx

from app.tide_data import _db_conn, get_hilo_predictions
from app.station_finder import find_stations_in_radius

NOAA_MDAPI = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"
APP_HEADER = "moon_and_tides/0.1"


def _get_flood_levels(station_id: str) -> dict | None:
    with _db_conn() as conn:
        row = conn.execute(
            "SELECT minor_ft, moderate_ft, major_ft FROM flood_levels WHERE station_id=?",
            (station_id,)
        ).fetchone()
    if row:
        return {"minor_ft": row[0], "moderate_ft": row[1], "major_ft": row[2]}

    url = f"{NOAA_MDAPI}/stations/{station_id}/floodlevels.json"
    try:
        resp = httpx.get(url, params={"application": APP_HEADER}, timeout=15)
        resp.raise_for_status()
        body = resp.json()
    except Exception:
        return None

    # NOAA floodlevels response nests data under "self" key
    fl = body.get("self")
    if not isinstance(fl, dict):
        return None
    minor = fl.get("minor")
    moderate = fl.get("moderate")
    major = fl.get("major")
    if minor is None:
        return None

    with _db_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO flood_levels "
            "(station_id, minor_ft, moderate_ft, major_ft, fetched_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (station_id, minor, moderate, major, datetime.utcnow().isoformat())
        )
    return {"minor_ft": minor, "moderate_ft": moderate, "major_ft": major}


def compute_extreme_thresholds(
    station_id: str,
    percentile_high: float = 0.90,
    percentile_low: float = 0.10,
) -> dict:
    from datetime import datetime, timedelta
    today = datetime.utcnow()
    one_year_ago = today - timedelta(days=365)
    begin = one_year_ago.strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    data = get_hilo_predictions(station_id, begin, end)

    highs = sorted(d["height_ft"] for d in data if d["type"] == "H")
    lows = sorted(d["height_ft"] for d in data if d["type"] == "L")

    if not highs or not lows:
        raise ValueError(f"No tide data for station {station_id}")

    high_idx = int(len(highs) * percentile_high)
    low_idx = int(len(lows) * percentile_low)
    return {
        "high_threshold_ft": highs[min(high_idx, len(highs) - 1)],
        "low_threshold_ft": lows[min(low_idx, len(lows) - 1)],
    }


def find_extreme_tides(
    station_id: str,
    begin_date: str,
    end_date: str,
    high_threshold_ft: float | None = None,
    low_threshold_ft: float | None = None,
) -> list[dict]:
    if high_threshold_ft is None or low_threshold_ft is None:
        thresholds = compute_extreme_thresholds(station_id)
        high_threshold_ft = high_threshold_ft or thresholds["high_threshold_ft"]
        low_threshold_ft = low_threshold_ft or thresholds["low_threshold_ft"]

    data = get_hilo_predictions(station_id, begin_date, end_date)
    results = []
    for item in data:
        if item["type"] == "H" and item["height_ft"] >= high_threshold_ft:
            results.append({**item, "extreme_type": "king_tide",
                            "threshold_ft": high_threshold_ft})
        elif item["type"] == "L" and item["height_ft"] <= low_threshold_ft:
            results.append({**item, "extreme_type": "extreme_low",
                            "threshold_ft": low_threshold_ft})
    return results


def find_extreme_in_radius(
    lat: float,
    lon: float,
    radius_miles: float,
    begin_date: str,
    end_date: str,
    percentile_threshold: float = 0.90,
) -> list[dict]:
    stations = find_stations_in_radius(lat, lon, radius_miles)
    results = []
    for s in stations:
        try:
            thresholds = compute_extreme_thresholds(s["id"])
            extremes = find_extreme_tides(
                s["id"], begin_date, end_date,
                high_threshold_ft=thresholds["high_threshold_ft"],
                low_threshold_ft=thresholds["low_threshold_ft"],
            )
            for e in extremes:
                results.append({
                    **e,
                    "station_id": s["id"],
                    "station_name": s["name"],
                    "distance_miles": s["distance_miles"],
                    "percentile": percentile_threshold,
                })
        except Exception:
            continue
    results.sort(key=lambda x: x["date"])
    return results


def check_flood_risk(station_id: str, begin_date: str, end_date: str) -> list[dict]:
    flood = _get_flood_levels(station_id)
    if not flood:
        return []

    data = get_hilo_predictions(station_id, begin_date, end_date)
    results = []
    for item in data:
        if item["type"] != "H":
            continue
        h = item["height_ft"]
        if flood["major_ft"] and h >= flood["major_ft"]:
            level = "major"
        elif flood["moderate_ft"] and h >= flood["moderate_ft"]:
            level = "moderate"
        elif h >= flood["minor_ft"]:
            level = "minor"
        else:
            continue
        results.append({
            "date": item["date"],
            "time": item["time"],
            "predicted_high_ft": h,
            "minor_ft": flood["minor_ft"],
            "flood_level": level,
        })
    return results
