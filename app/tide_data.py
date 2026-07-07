import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import httpx

CACHE_DB = Path(__file__).parent.parent / "cache" / "tides.db"
NOAA_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
APP_HEADER = "moon_and_tides/0.1"
CACHE_DAYS_PREDICTIONS_FUTURE = 365   # current/future year — check once a year
# Past years: never expire — NOAA predictions for completed years are immutable


def _db_conn() -> sqlite3.Connection:
    CACHE_DB.parent.mkdir(exist_ok=True)
    # 30s busy timeout: map/status fetches from a thread pool, so brief
    # concurrent writes to the cache are expected
    conn = sqlite3.connect(str(CACHE_DB), timeout=30)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            station_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            product TEXT NOT NULL,
            datum TEXT NOT NULL,
            units TEXT NOT NULL,
            json_data TEXT NOT NULL,
            fetched_at TIMESTAMP NOT NULL,
            PRIMARY KEY (station_id, year, product, datum, units)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id TEXT PRIMARY KEY,
            name TEXT,
            lat REAL,
            lon REAL,
            state TEXT,
            tidal INTEGER,
            harmonic INTEGER,
            json_data TEXT,
            fetched_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tidal_ranges (
            station_id TEXT PRIMARY KEY,
            mean_range_ft REAL,
            mean_high_ft REAL,
            mean_low_ft REAL,
            computed_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flood_levels (
            station_id TEXT PRIMARY KEY,
            minor_ft REAL,
            moderate_ft REAL,
            major_ft REAL,
            fetched_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS perigean_events (
            year INTEGER PRIMARY KEY,
            json_data TEXT,
            computed_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS solar_days (
            lat  REAL NOT NULL,
            lon  REAL NOT NULL,
            date TEXT NOT NULL,
            json_data TEXT NOT NULL,
            PRIMARY KEY (lat, lon, date)
        )
    """)
    conn.commit()
    return conn


def _cache_get(station_id: str, year: int, product: str, datum: str, units: str):
    with _db_conn() as conn:
        row = conn.execute(
            "SELECT json_data, fetched_at FROM predictions "
            "WHERE station_id=? AND year=? AND product=? AND datum=? AND units=?",
            (station_id, year, product, datum, units)
        ).fetchone()
    if row is None:
        return None
    json_data, fetched_at_str = row
    current_year = datetime.utcnow().year
    if year < current_year:
        # Past-year predictions are immutable — keep forever
        return json.loads(json_data)
    # Current/future year: refresh once per year
    fetched_at = datetime.fromisoformat(fetched_at_str)
    if datetime.utcnow() - fetched_at > timedelta(days=CACHE_DAYS_PREDICTIONS_FUTURE):
        return None
    return json.loads(json_data)


def _cache_put(station_id: str, year: int, product: str, datum: str, units: str, data):
    with _db_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO predictions "
            "(station_id, year, product, datum, units, json_data, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (station_id, year, product, datum, units, json.dumps(data), datetime.utcnow().isoformat())
        )


def _fetch_noaa_hilo(station_id: str, year: int, datum: str, units: str, time_zone: str) -> list[dict]:
    begin = f"{year}0101"
    end = f"{year}1231"
    params = {
        "product": "predictions",
        "application": APP_HEADER,
        "begin_date": begin,
        "end_date": end,
        "datum": datum,
        "station": station_id,
        "time_zone": time_zone,
        "interval": "hilo",
        "units": units,
        "format": "json",
    }
    resp = httpx.get(NOAA_BASE, params=params, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise ValueError(f"NOAA error: {body['error'].get('message', body['error'])}")
    raw = body.get("predictions", [])
    return _parse_hilo(raw)


def to_12h(time_str: str) -> str:
    """Convert 'HH:MM' to '12-hour AM/PM' (e.g. '04:21' → '4:21 AM')."""
    h, m = int(time_str[:2]), int(time_str[3:])
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def _add_12h(records: list[dict]) -> list[dict]:
    """Add time_12h to any record that has a 'time' field but is missing time_12h."""
    for r in records:
        if "time" in r and "time_12h" not in r:
            r["time_12h"] = to_12h(r["time"])
    return records


def _parse_hilo(raw: list[dict]) -> list[dict]:
    result = []
    for item in raw:
        dt_str = item.get("t", "")
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        time_24 = dt.strftime("%H:%M")
        result.append({
            "date": dt.strftime("%Y-%m-%d"),
            "time": time_24,
            "height_ft": float(item.get("v", 0)),
            "type": item.get("type", "").upper(),
        })
    return result


def get_hilo_predictions(
    station_id: str,
    begin_date: str,
    end_date: str,
    datum: str = "MLLW",
    units: str = "english",
    time_zone: str = "lst_ldt",
) -> list[dict]:
    begin_dt = datetime.strptime(begin_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")

    years = range(begin_dt.year, end_dt.year + 1)
    all_records: list[dict] = []

    for year in years:
        cached = _cache_get(station_id, year, "hilo", datum, units)
        if cached is not None:
            all_records.extend(cached)
            continue

        try:
            year_data = _fetch_noaa_hilo(station_id, year, datum, units, time_zone)
            _cache_put(station_id, year, "hilo", datum, units, year_data)
            all_records.extend(year_data)
        except Exception:
            # On fetch failure, try stale cache (no expiry check)
            with _db_conn() as conn:
                row = conn.execute(
                    "SELECT json_data FROM predictions "
                    "WHERE station_id=? AND year=? AND product='hilo' AND datum=? AND units=?",
                    (station_id, year, datum, units)
                ).fetchone()
            if row:
                all_records.extend(json.loads(row[0]))
            else:
                raise

    begin_str = begin_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    filtered = [r for r in all_records if begin_str <= r["date"] <= end_str]
    return _add_12h(filtered)


def synthesize_curve_from_hilo(
    station_id: str,
    date: str,
    datum: str = "MLLW",
    units: str = "english",
) -> list[dict]:
    """Approximate a 6-minute water level curve by cosine interpolation between
    the station's own high/low predictions. Used for subordinate stations,
    where NOAA publishes corrected hilo but no 6-minute product. Includes the
    neighboring days' events so the curve is continuous across midnight."""
    import math

    dt = datetime.strptime(date, "%Y%m%d")
    begin = (dt - timedelta(days=1)).strftime("%Y%m%d")
    end = (dt + timedelta(days=1)).strftime("%Y%m%d")
    hilo = get_hilo_predictions(station_id, begin, end, datum=datum, units=units)

    events = sorted(
        (datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H:%M"), r["height_ft"])
        for r in hilo
    )
    if len(events) < 2:
        return []

    records = []
    t = dt
    day_end = dt + timedelta(days=1)
    i = 0  # index of the first event at/after t, advanced monotonically
    while t < day_end:
        while i < len(events) and events[i][0] <= t:
            i += 1
        if i == 0:
            height = events[0][1]           # before first known event: clamp
        elif i == len(events):
            height = events[-1][1]          # after last known event: clamp
        else:
            (t1, h1), (t2, h2) = events[i - 1], events[i]
            u = (t - t1).total_seconds() / (t2 - t1).total_seconds()
            height = h1 + (h2 - h1) * (1 - math.cos(math.pi * u)) / 2
        records.append({
            "date": t.strftime("%Y-%m-%d"),
            "time": t.strftime("%H:%M"),
            "height_ft": round(height, 3),
            "synthetic": True,
        })
        t += timedelta(minutes=6)
    return _add_12h(records)


def get_water_level_curve(
    station_id: str,
    date: str,
    datum: str = "MLLW",
    units: str = "english",
) -> list[dict]:
    from app.station_finder import is_subordinate_station

    dt = datetime.strptime(date, "%Y%m%d")
    year = dt.year
    cached = _cache_get(station_id, year, "curve", datum, units)

    if cached is not None:
        date_str = dt.strftime("%Y-%m-%d")
        return _add_12h([r for r in cached if r["date"] == date_str])

    # Subordinate stations have no 6-minute product — synthesize from their
    # NOAA-corrected hilo instead of making a request that will fail.
    if is_subordinate_station(station_id):
        return synthesize_curve_from_hilo(station_id, date, datum, units)

    params = {
        "product": "predictions",
        "application": APP_HEADER,
        "begin_date": f"{year}0101",
        "end_date": f"{year}1231",
        "datum": datum,
        "station": station_id,
        "time_zone": "lst_ldt",
        "interval": "6",
        "units": units,
        "format": "json",
    }
    resp = httpx.get(NOAA_BASE, params=params, timeout=60)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        msg = str(body["error"].get("message", body["error"]))
        if "No Predictions data" in msg:
            # Station has hilo but no 6-minute product (subordinate not yet
            # flagged in the cached station list) — synthesize instead.
            return synthesize_curve_from_hilo(station_id, date, datum, units)
        raise ValueError(f"NOAA error: {msg}")

    raw = body.get("predictions", [])
    records = []
    for item in raw:
        dt_str = item.get("t", "")
        try:
            dt_parsed = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        records.append({
            "date": dt_parsed.strftime("%Y-%m-%d"),
            "time": dt_parsed.strftime("%H:%M"),
            "height_ft": float(item.get("v", 0)),
        })

    _cache_put(station_id, year, "curve", datum, units, records)
    date_str = dt.strftime("%Y-%m-%d")
    day_records = [r for r in records if r["date"] == date_str]
    return _add_12h(day_records)


def get_station_tidal_range(station_id: str) -> dict:
    with _db_conn() as conn:
        row = conn.execute(
            "SELECT mean_range_ft, mean_high_ft, mean_low_ft FROM tidal_ranges WHERE station_id=?",
            (station_id,)
        ).fetchone()
    if row:
        return {"mean_range_ft": row[0], "mean_high_ft": row[1], "mean_low_ft": row[2]}

    today = datetime.utcnow()
    one_year_ago = today - timedelta(days=365)
    begin = one_year_ago.strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    data = get_hilo_predictions(station_id, begin, end)

    highs = [d["height_ft"] for d in data if d["type"] == "H"]
    lows = [d["height_ft"] for d in data if d["type"] == "L"]

    if not highs or not lows:
        raise ValueError(f"Insufficient data for station {station_id}")

    mean_high = sum(highs) / len(highs)
    mean_low = sum(lows) / len(lows)
    mean_range = mean_high - mean_low

    with _db_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tidal_ranges "
            "(station_id, mean_range_ft, mean_high_ft, mean_low_ft, computed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (station_id, mean_range, mean_high, mean_low, datetime.utcnow().isoformat())
        )

    return {"mean_range_ft": mean_range, "mean_high_ft": mean_high, "mean_low_ft": mean_low}
