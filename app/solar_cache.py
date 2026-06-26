"""
Cache layer for astronomical solar calculations (sunrise/sunset).
Solar times are pure calculations — given the same lat/lon/date they
never change, so we cache them indefinitely (no expiry needed).
"""
import json
import math
from datetime import timedelta
from zoneinfo import ZoneInfo

import ephem
from timezonefinder import TimezoneFinder

from app.tide_data import _db_conn, to_12h

_tf = TimezoneFinder()


def _round_coord(v: float) -> float:
    """Round lat/lon to 4 decimal places (~11 m precision) for cache keys."""
    return round(v, 4)


def _compute_solar(lat: float, lon: float, date_str: str, tz: ZoneInfo) -> dict:
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.horizon = "-0:34"
    obs.date = date_str
    sun = ephem.Sun()
    try:
        sr_utc = obs.next_rising(sun).datetime()
        obs.date = date_str          # reset — next_rising mutates obs.date
        ss_utc = obs.next_setting(sun).datetime()
        sr = sr_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        ss = ss_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        sr_str = sr.strftime("%H:%M")
        ss_str = ss.strftime("%H:%M")
        dl = (ss.hour * 60 + ss.minute) - (sr.hour * 60 + sr.minute)
        if dl < 0:
            dl += 1440
        return {
            "date": date_str,
            "sunrise":     sr_str,
            "sunset":      ss_str,
            "sunrise_12h": to_12h(sr_str),
            "sunset_12h":  to_12h(ss_str),
            "daylight_hours": round(dl / 60, 2),
        }
    except ephem.AlwaysUpError:
        return {"date": date_str, "sunrise": None, "sunset": None,
                "sunrise_12h": None, "sunset_12h": None, "daylight_hours": 24.0}
    except ephem.NeverUpError:
        return {"date": date_str, "sunrise": None, "sunset": None,
                "sunrise_12h": None, "sunset_12h": None, "daylight_hours": 0.0}


def get_solar_day(lat: float, lon: float, date_str: str) -> dict:
    """Return solar data for one day, using the DB cache."""
    lat_r = _round_coord(lat)
    lon_r = _round_coord(lon)

    with _db_conn() as conn:
        row = conn.execute(
            "SELECT json_data FROM solar_days WHERE lat=? AND lon=? AND date=?",
            (lat_r, lon_r, date_str)
        ).fetchone()
    if row:
        return json.loads(row[0])

    tz_name = _tf.timezone_at(lat=lat, lng=lon) or "UTC"
    result = _compute_solar(lat, lon, date_str, ZoneInfo(tz_name))

    with _db_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO solar_days (lat, lon, date, json_data) VALUES (?,?,?,?)",
            (lat_r, lon_r, date_str, json.dumps(result))
        )
    return result


def get_solar_range(lat: float, lon: float, begin_str: str, end_str: str) -> list[dict]:
    """Return solar data for every day in [begin, end], using the DB cache."""
    from datetime import date as dt_date
    lat_r = _round_coord(lat)
    lon_r = _round_coord(lon)

    begin = dt_date.fromisoformat(begin_str)
    end   = dt_date.fromisoformat(end_str)

    # Fetch whatever is already cached
    with _db_conn() as conn:
        rows = conn.execute(
            "SELECT date, json_data FROM solar_days "
            "WHERE lat=? AND lon=? AND date BETWEEN ? AND ? ORDER BY date",
            (lat_r, lon_r, begin_str, end_str)
        ).fetchall()
    cached = {r[0]: json.loads(r[1]) for r in rows}

    # Compute and cache any missing days
    tz_name = _tf.timezone_at(lat=lat, lng=lon) or "UTC"
    tz = ZoneInfo(tz_name)
    results = []
    current = begin
    while current <= end:
        date_str = current.isoformat()
        if date_str in cached:
            results.append(cached[date_str])
        else:
            data = _compute_solar(lat, lon, date_str, tz)
            with _db_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO solar_days (lat, lon, date, json_data) VALUES (?,?,?,?)",
                    (lat_r, lon_r, date_str, json.dumps(data))
                )
            results.append(data)
        current += timedelta(days=1)

    return results
