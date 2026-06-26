from datetime import datetime, timedelta, date

import ephem


BORE_OFFSETS = {
    "turnagain_arm_ak": {"ref_station": "9455090", "offset_hours": 2.5},
}


def _get_solar_day(lat: float, lon: float, date_str: str) -> dict:
    """Get sunrise/sunset for a given lat/lon and date using ephem."""
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.date = date_str
    obs.horizon = "-0:34"  # standard refraction

    sun = ephem.Sun()
    try:
        sunrise = obs.next_rising(sun).datetime()
        sunset = obs.next_setting(sun).datetime()
    except ephem.AlwaysUpError:
        return {"sunrise": None, "sunset": None, "daylight_hours": 24.0}
    except ephem.NeverUpError:
        return {"sunrise": None, "sunset": None, "daylight_hours": 0.0}

    daylight = (sunset - sunrise).total_seconds() / 3600
    return {
        "sunrise": sunrise.strftime("%H:%M"),
        "sunset": sunset.strftime("%H:%M"),
        "daylight_hours": round(daylight, 2),
    }


def get_slack_water(station_id: str, date: str) -> list[dict]:
    """Find slack water times (inflection points) from 6-minute water level curve."""
    from app.tide_data import get_water_level_curve
    dt = datetime.strptime(date, "%Y-%m-%d")
    curve = get_water_level_curve(station_id, dt.strftime("%Y%m%d"))

    if len(curve) < 3:
        return []

    heights = [r["height_ft"] for r in curve]
    times = [r["time"] for r in curve]

    slacks = []
    for i in range(1, len(heights) - 1):
        prev_diff = heights[i] - heights[i - 1]
        next_diff = heights[i + 1] - heights[i]
        # Sign change = inflection point (tide reversal)
        if prev_diff * next_diff < 0:
            direction = "high_to_low" if prev_diff > 0 else "low_to_high"
            slacks.append({"time": times[i], "between": direction})
    return slacks


def get_tidepooling_windows(
    station_id: str,
    begin_date: str,
    end_date: str,
    lat: float,
    lon: float,
) -> list[dict]:
    """Find days where lowest tide occurs during daylight hours."""
    from app.tide_data import get_hilo_predictions

    begin_dt = datetime.strptime(begin_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    data = get_hilo_predictions(station_id, begin_date, end_date)

    # Group lows by date
    lows_by_date: dict[str, list[dict]] = {}
    for item in data:
        if item["type"] == "L":
            lows_by_date.setdefault(item["date"], []).append(item)

    results = []
    current = begin_dt
    while current <= end_dt:
        date_str = current.strftime("%Y-%m-%d")
        lows = lows_by_date.get(date_str, [])
        if lows:
            lowest = min(lows, key=lambda x: x["height_ft"])
            solar = _get_solar_day(lat, lon, date_str)

            if solar["sunrise"] and solar["sunset"]:
                low_time = lowest["time"]
                if solar["sunrise"] <= low_time <= solar["sunset"]:
                    # Score: lower height + closer to solar noon = better
                    noon = _time_to_minutes(solar["sunrise"]) + (
                        _time_to_minutes(solar["sunset"]) - _time_to_minutes(solar["sunrise"])
                    ) / 2
                    low_minutes = _time_to_minutes(low_time)
                    time_from_noon = abs(low_minutes - noon) / 60
                    score = -lowest["height_ft"] - time_from_noon * 0.1
                    results.append({
                        "date": date_str,
                        "low_tide_time": low_time,
                        "low_height_ft": lowest["height_ft"],
                        "sunrise": solar["sunrise"],
                        "sunset": solar["sunset"],
                        "score": round(score, 3),
                    })
        current += timedelta(days=1)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _time_to_minutes(t: str) -> float:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _find_perigee_near(moon: "ephem.Moon", syzygy_date, window_days: float = 7.0):
    """Find the nearest perigee (minimum moon distance) within ±window_days of a date."""
    min_dist = float("inf")
    min_date = syzygy_date
    d = ephem.Date(float(syzygy_date) - window_days)
    end = ephem.Date(float(syzygy_date) + window_days)
    step = 6.0 / 24.0  # 6-hour steps
    while d <= end:
        moon.compute(d)
        if moon.earth_distance < min_dist:
            min_dist = moon.earth_distance
            min_date = d
        d = ephem.Date(float(d) + step)
    return min_date, min_dist


def get_perigean_spring_tides(year: int) -> list[dict]:
    """Find dates where lunar perigee coincides with new/full moon (syzygy)."""
    from app.tide_data import _db_conn
    import json as _json

    with _db_conn() as conn:
        row = conn.execute(
            "SELECT json_data FROM perigean_events WHERE year=?", (year,)
        ).fetchone()
    if row:
        return _json.loads(row[0])

    results = []
    moon = ephem.Moon()
    year_end = ephem.Date(f"{year + 1}/1/1")
    seen_dates: set[str] = set()

    d = ephem.Date(f"{year}/1/1")
    while True:
        nm = ephem.next_new_moon(d)
        fm = ephem.next_full_moon(d)
        if float(nm) > float(year_end) and float(fm) > float(year_end):
            break

        for syzygy_date, phase in [(nm, "new moon"), (fm, "full moon")]:
            if float(syzygy_date) > float(year_end):
                continue
            syzygy_year = ephem.Date(syzygy_date).datetime().year
            if syzygy_year != year:
                continue

            perigee_d, perigee_dist = _find_perigee_near(moon, syzygy_date)
            diff_days = abs(float(perigee_d) - float(syzygy_date))

            if diff_days <= 1.5:
                syzygy_dt = ephem.Date(syzygy_date).datetime()
                date_str = syzygy_dt.strftime("%Y-%m-%d")
                if date_str not in seen_dates:
                    seen_dates.add(date_str)
                    dist_km = round(perigee_dist * 149597870.7, 0)
                    results.append({
                        "date": date_str,
                        "moon_phase": phase,
                        "perigee_distance_km": dist_km,
                        "description": (
                            f"Perigean Spring Tide: {phase} within "
                            f"{diff_days * 24:.1f}h of perigee ({dist_km:.0f} km)"
                        ),
                    })

        d = ephem.Date(float(nm) + 1)

    results.sort(key=lambda x: x["date"])

    with _db_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO perigean_events (year, json_data, computed_at) VALUES (?, ?, ?)",
            (year, _json.dumps(results), datetime.utcnow().isoformat())
        )

    return results


def get_tidal_bore_times(location_name: str, date: str) -> dict | None:
    key = location_name.lower().replace(" ", "_")
    if key not in BORE_OFFSETS:
        return None

    bore = BORE_OFFSETS[key]
    from app.tide_data import get_hilo_predictions
    d = datetime.strptime(date, "%Y-%m-%d")
    begin = d.strftime("%Y%m%d")
    data = get_hilo_predictions(bore["ref_station"], begin, begin)

    lows = [item for item in data if item["type"] == "L"]
    if not lows:
        return None

    results = []
    for low in lows:
        low_dt = datetime.strptime(f"{low['date']} {low['time']}", "%Y-%m-%d %H:%M")
        bore_dt = low_dt + timedelta(hours=bore["offset_hours"])
        results.append({
            "bore_time": bore_dt.strftime("%H:%M"),
            "ref_low_time": low["time"],
            "offset_hours": bore["offset_hours"],
        })
    return {"location": location_name, "date": date, "bore_times": results}
