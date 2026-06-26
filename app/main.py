from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Tideline", version="0.1.0")


@app.get("/api/v1/solar-day")
def solar_day(lat: float = Query(...), lon: float = Query(...), date: str = Query(...)):
    """Return sunrise/sunset in the station's local timezone (cached indefinitely)."""
    from app.solar_cache import get_solar_day
    return get_solar_day(lat, lon, date)


@app.get("/api/v1/solar-range")
def solar_range(
    lat: float = Query(...),
    lon: float = Query(...),
    begin: str = Query(...),
    end:   str = Query(...),
):
    """Return sunrise/sunset for every day in [begin, end] (cached indefinitely)."""
    from app.solar_cache import get_solar_range
    return get_solar_range(lat, lon, begin, end)


class GeocodeRequest(BaseModel):
    address: str


@app.post("/geocode")
def geocode(req: GeocodeRequest):
    from app.geocode import geocode_address
    try:
        return geocode_address(req.address)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/stations/nearest")
def stations_nearest(
    lat: float = Query(...),
    lon: float = Query(...),
    count: int = Query(5),
    require_harmonic: bool = Query(False),
):
    from app.station_finder import find_nearest_stations, get_tidal_type
    stations = find_nearest_stations(lat, lon, max_results=count, require_harmonic=require_harmonic)
    result = []
    for s in stations:
        try:
            tt = get_tidal_type(s["id"])
            tidal_type = tt["type"]
        except Exception:
            tidal_type = "unknown"
        result.append({**s, "tidal_type": tidal_type})
    return result


@app.get("/api/v1/stations/radius")
def stations_radius(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_miles: float = Query(75.0),
):
    from app.station_finder import find_stations_in_radius
    return find_stations_in_radius(lat, lon, radius_miles)


@app.get("/api/v1/station/{station_id}")
def station_detail(station_id: str):
    from app.station_finder import get_all_stations, get_tidal_type
    from app.tide_data import get_station_tidal_range, _db_conn

    stations = get_all_stations()
    station = next((s for s in stations if s["id"] == station_id), None)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    try:
        tr = get_station_tidal_range(station_id)
    except Exception:
        tr = {"mean_range_ft": None, "mean_high_ft": None, "mean_low_ft": None}

    try:
        tt = get_tidal_type(station_id)
        tidal_type = tt["type"]
    except Exception:
        tidal_type = "unknown"

    with _db_conn() as conn:
        flood = conn.execute(
            "SELECT minor_ft, moderate_ft, major_ft FROM flood_levels WHERE station_id=?",
            (station_id,)
        ).fetchone()

    return {
        **station,
        "tidal_type": tidal_type,
        "mean_range_ft": tr["mean_range_ft"],
        "mean_high_ft": tr["mean_high_ft"],
        "mean_low_ft": tr["mean_low_ft"],
        "has_flood_thresholds": flood is not None,
        "flood_minor_ft": flood[0] if flood else None,
        "flood_moderate_ft": flood[1] if flood else None,
    }


@app.get("/api/v1/tides/day")
def tides_day(
    station_id: str = Query(...),
    date: str = Query(...),  # YYYY-MM-DD
    datum: str = Query("MLLW"),
    units: str = Query("english"),
):
    from app.tide_data import get_hilo_predictions, get_water_level_curve
    d = datetime.strptime(date, "%Y-%m-%d")
    begin = d.strftime("%Y%m%d")
    end = begin
    hilo = get_hilo_predictions(station_id, begin, end, datum=datum, units=units)
    try:
        curve = get_water_level_curve(station_id, begin, datum=datum, units=units)
    except Exception:
        curve = []
    return {"hilo": hilo, "curve": curve}


@app.get("/api/v1/tides/range")
def tides_range(
    station_id: str = Query(...),
    begin: str = Query(...),  # YYYY-MM-DD
    end: str = Query(...),    # YYYY-MM-DD
):
    from app.tide_data import get_hilo_predictions
    begin_fmt = datetime.strptime(begin, "%Y-%m-%d").strftime("%Y%m%d")
    end_fmt = datetime.strptime(end, "%Y-%m-%d").strftime("%Y%m%d")
    hilo = get_hilo_predictions(station_id, begin_fmt, end_fmt)
    return {"hilo": hilo}


@app.get("/api/v1/tides/year-summary")
def tides_year_summary(
    station_id: str = Query(...),
    year: int = Query(...),
):
    from app.tide_data import get_hilo_predictions
    data = get_hilo_predictions(station_id, f"{year}0101", f"{year}1231")

    monthly_highs = [[] for _ in range(12)]
    monthly_lows = [[] for _ in range(12)]
    for item in data:
        mo = int(item["date"][5:7]) - 1
        if item["type"] == "H":
            monthly_highs[mo].append(item["height_ft"])
        else:
            monthly_lows[mo].append(item["height_ft"])

    mean_high = [sum(v) / len(v) if v else None for v in monthly_highs]
    mean_low = [sum(v) / len(v) if v else None for v in monthly_lows]

    highs = sorted([i for i in data if i["type"] == "H"], key=lambda x: x["height_ft"], reverse=True)
    lows = sorted([i for i in data if i["type"] == "L"], key=lambda x: x["height_ft"])

    return {
        "monthly_mean_high": mean_high,
        "monthly_mean_low": mean_low,
        "extreme_highs": highs[:10],
        "extreme_lows": lows[:10],
    }


@app.get("/api/v1/special-events")
def special_events(
    station_id: str = Query(...),
    year: int = Query(...),
    lat: float = Query(None),
    lon: float = Query(None),
    radius_miles: float = Query(75.0),
):
    from app.special_events import get_perigean_spring_tides, get_tidepooling_windows
    from app.alert_engine import find_extreme_tides, compute_extreme_thresholds, check_flood_risk

    today = datetime.utcnow().strftime("%Y-%m-%d")
    year_end = f"{year}-12-31"

    # Perigean spring tides for the whole year, filtered to upcoming
    try:
        perigean = [e for e in get_perigean_spring_tides(year) if e["date"] >= today]
    except Exception:
        perigean = []

    # King tide alerts: rest of year using 90th-percentile threshold
    try:
        thresholds = compute_extreme_thresholds(station_id)
        begin_fmt = today.replace("-", "")
        end_fmt = year_end.replace("-", "")
        king_tides = find_extreme_tides(
            station_id, begin_fmt, end_fmt,
            high_threshold_ft=thresholds["high_threshold_ft"],
            low_threshold_ft=thresholds["low_threshold_ft"],
        )
    except Exception:
        king_tides = []

    # Flood risk events
    try:
        flood = check_flood_risk(station_id, today.replace("-", ""), year_end.replace("-", ""))
    except Exception:
        flood = []

    # Tidepooling windows (requires lat/lon)
    tidepooling: list = []
    if lat is not None and lon is not None:
        try:
            # Look 60 days ahead
            from datetime import timedelta
            end_tp = (datetime.utcnow() + timedelta(days=60)).strftime("%Y%m%d")
            tidepooling = get_tidepooling_windows(
                station_id, today.replace("-", ""), end_tp, lat, lon
            )[:10]
        except Exception:
            tidepooling = []

    return {
        "perigean_spring_tides": perigean,
        "king_tides": king_tides[:30],
        "flood_risk": flood[:20],
        "tidepooling_windows": tidepooling,
        "slack_water": [],
        "radius_alerts": [],
    }


@app.get("/api/v1/ics-preview")
def ics_preview(
    station_id: str = Query(...),
    year: int = Query(...),
    lat: float = Query(None),
    lon: float = Query(None),
    options: str = Query("hilo,alerts,perigean,flood"),
    radius_miles: float = Query(75.0),
):
    """Return event counts for an ICS build without generating the file."""
    from app.ics_builder import build_tidal_ics
    opts = {o.strip(): True for o in options.split(",")}
    _, counts = build_tidal_ics(station_id, year, opts, lat=lat, lon=lon, radius_miles=radius_miles)
    return {"counts": counts, "total": sum(counts.values())}


@app.get("/calendar/{year}/{lat_lon}.ics")
def calendar_ics(year: int, lat_lon: str, options: str = Query("hilo")):
    try:
        lat_str, lon_str = lat_lon.split(",")
        lat, lon = float(lat_str), float(lon_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lat,lon format")

    from app.station_finder import find_nearest_stations
    from app.ics_builder import build_tidal_ics
    stations = find_nearest_stations(lat, lon, max_results=1)
    if not stations:
        raise HTTPException(status_code=404, detail="No stations found")

    station_id = stations[0]["id"]
    opts = {o: True for o in options.split(",")}
    ics_bytes, _ = build_tidal_ics(station_id, year, opts, lat=lat, lon=lon)

    return StreamingResponse(
        iter([ics_bytes]),
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="tides_{station_id}_{year}.ics"'},
    )


@app.get("/calendar/{year}/{lat_lon}-alerts.ics")
def calendar_alerts_ics(year: int, lat_lon: str):
    try:
        lat_str, lon_str = lat_lon.split(",")
        lat, lon = float(lat_str), float(lon_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lat,lon format")

    from app.station_finder import find_nearest_stations
    from app.ics_builder import build_alerts_only_ics
    stations = find_nearest_stations(lat, lon, max_results=1)
    if not stations:
        raise HTTPException(status_code=404, detail="No stations found")

    station_id = stations[0]["id"]
    ics_bytes, _ = build_alerts_only_ics(station_id, year, lat=lat, lon=lon)

    return StreamingResponse(
        iter([ics_bytes]),
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="alerts_{station_id}_{year}.ics"'},
    )
