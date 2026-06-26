from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Tideline", version="0.1.0")


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
    # Placeholder — implemented in Phase 4
    return {
        "tidepooling_windows": [],
        "slack_water": [],
        "perigean_spring_tides": [],
        "radius_alerts": [],
        "flood_risk": [],
    }


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
    ics_bytes = build_tidal_ics(station_id, year, opts)

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
    ics_bytes = build_alerts_only_ics(station_id, year)

    return StreamingResponse(
        iter([ics_bytes]),
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="alerts_{station_id}_{year}.ics"'},
    )
