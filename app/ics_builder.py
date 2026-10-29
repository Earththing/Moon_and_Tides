from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from app.tide_data import get_hilo_predictions, get_station_tidal_range


def _station_meta(station_id: str, lat: float | None = None,
                  lon: float | None = None) -> tuple[str, ZoneInfo, float | None, float | None]:
    """Return (name, timezone, lat, lon) for a station.

    lat/lon are the station's own coordinates when known, else the caller's."""
    from app.station_finder import get_station, station_timezone
    s = get_station(station_id)
    name = s["name"] if s else station_id
    if s:
        lat, lon = s["lat"], s["lon"]
    return name, station_timezone(station_id, lat, lon), lat, lon


def _make_uid(station_id: str, date_str: str, time_str: str, tag: str) -> str:
    hhmm = time_str.replace(":", "")
    return f"tide-{station_id}-{date_str}-{hhmm}-{tag}@tideline"


def _ft_to_m(ft: float) -> float:
    return round(ft * 0.3048, 2)


def _build_calendar(station_id: str, year: int, station_name: str, tz: ZoneInfo) -> Calendar:
    # VTIMEZONE is generated from the events' TZIDs in build_tidal_ics.
    cal = Calendar()
    cal.add("prodid", "-//Tideline//Moon and Tides//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", f"Tides — {station_name} {year}")
    cal.add("x-wr-timezone", tz.key)
    return cal


def _add_hilo_event(cal: Calendar, item: dict, next_item: dict | None,
                    station_id: str, station_name: str, tz: ZoneInfo, counts: dict) -> None:
    h      = item["height_ft"]
    h_m    = _ft_to_m(h)
    ttype  = item["type"]
    date_s = item["date"]
    time_s = item["time"]
    t12    = item.get("time_12h", time_s)
    dt     = datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)

    if ttype == "H":
        summary = f"🌊 High Tide — {h} ft"
        counts["hilo_high"] += 1
    else:
        summary = f"🏖 Low Tide — {h} ft"
        counts["hilo_low"] += 1

    if next_item:
        nxt_label = "low" if ttype == "H" else "high"
        nxt_t = f"{next_item['time']} ({next_item.get('time_12h', next_item['time'])})"
        desc = (
            f"Height: {h} ft ({h_m} m)\n"
            f"Datum: MLLW\n"
            f"Station: {station_name} ({station_id})\n"
            f"Next {nxt_label} tide: {nxt_t} — {next_item['height_ft']} ft"
        )
    else:
        desc = f"Height: {h} ft ({h_m} m)\nDatum: MLLW\nStation: {station_name} ({station_id})"

    ev = Event()
    ev.add("uid",         _make_uid(station_id, date_s, time_s, ttype))
    ev.add("summary",     summary)
    ev.add("dtstart",     dt)
    ev.add("dtend",       dt + timedelta(minutes=15))
    ev.add("description", desc)
    cal.add_component(ev)


def _add_allday(cal: Calendar, uid: str, summary: str, date_str: str,
                description: str = "") -> None:
    d = date.fromisoformat(date_str)
    ev = Event()
    ev.add("uid",     uid)
    ev.add("summary", summary)
    ev.add("dtstart", d)
    ev.add("dtend",   d + timedelta(days=1))
    if description:
        ev.add("description", description)
    cal.add_component(ev)


def build_tidal_ics(
    station_id: str,
    year: int,
    options: dict | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_miles: float = 75.0,
) -> tuple[bytes, dict]:
    """
    Build a full ICS calendar.

    Returns (ics_bytes, counts) where counts is a dict of event type → count.
    options keys: hilo, alerts, slack, tidepooling, flood, perigean, radius
    """
    if options is None:
        options = {"hilo": True}

    # Tidepooling sunrise/sunset and the radius-alert center default to the
    # station itself, so a station-addressed calendar needs no coordinates.
    station_name, tz, lat, lon = _station_meta(station_id, lat, lon)
    cal   = _build_calendar(station_id, year, station_name, tz)
    data  = get_hilo_predictions(station_id, f"{year}0101", f"{year}1231")
    counts: dict = defaultdict(int)

    from app.alert_engine import compute_extreme_thresholds
    try:
        th = compute_extreme_thresholds(station_id, year=year)
        high_thresh, low_thresh = th["high_threshold_ft"], th["low_threshold_ft"]
    except ValueError:
        high_thresh, low_thresh = 999.0, -999.0

    # ── hilo + extreme alerts ────────────────────────────────────────────────
    for i, item in enumerate(data):
        h      = item["height_ft"]
        ttype  = item["type"]
        date_s = item["date"]
        time_s = item["time"]
        d      = date.fromisoformat(date_s)

        is_extreme_high = ttype == "H" and h >= high_thresh
        is_extreme_low  = ttype == "L" and h <= low_thresh

        if options.get("alerts", True) and is_extreme_high:
            _add_allday(cal,
                uid=_make_uid(station_id, date_s, time_s, "EH"),
                summary=f"⚠️ King Tide — {h} ft",
                date_str=date_s,
                description=f"Height: {h} ft\nStation: {station_name} ({station_id})",
            )
            counts["king_tide"] += 1

        if options.get("alerts", True) and is_extreme_low:
            _add_allday(cal,
                uid=_make_uid(station_id, date_s, time_s, "EL"),
                summary=f"⚠️ Extreme Low — {h} ft",
                date_str=date_s,
                description=f"Height: {h} ft\nStation: {station_name} ({station_id})",
            )
            counts["extreme_low"] += 1

        if options.get("hilo", True):
            next_item = data[i + 1] if i + 1 < len(data) else None
            _add_hilo_event(cal, item, next_item, station_id, station_name, tz, counts)

    # ── perigean spring tides ────────────────────────────────────────────────
    if options.get("perigean", False):
        try:
            from app.special_events import get_perigean_spring_tides
            for e in get_perigean_spring_tides(year, tz=tz):
                _add_allday(cal,
                    uid=f"perigean-{station_id}-{e['date']}@tideline",
                    summary=f"🌕 Perigean Spring Tide",
                    date_str=e["date"],
                    description=e["description"],
                )
                counts["perigean"] += 1
        except Exception:
            pass

    # ── flood risk ───────────────────────────────────────────────────────────
    if options.get("flood", False):
        try:
            from app.alert_engine import check_flood_risk
            for e in check_flood_risk(station_id, f"{year}0101", f"{year}1231"):
                _add_allday(cal,
                    uid=f"flood-{station_id}-{e['date']}@tideline",
                    summary=f"🚨 Flood Risk: {e['flood_level']} — {e['predicted_high_ft']} ft",
                    date_str=e["date"],
                    description=(
                        f"Flood level: {e['flood_level']}\n"
                        f"Predicted high: {e['predicted_high_ft']} ft\n"
                        f"Minor threshold: {e['minor_ft']} ft\n"
                        f"Station: {station_name} ({station_id})"
                    ),
                )
                counts["flood_risk"] += 1
        except Exception:
            pass

    # ── tidepooling windows ──────────────────────────────────────────────────
    if options.get("tidepooling", False) and lat is not None and lon is not None:
        try:
            from app.special_events import get_tidepooling_windows
            for e in get_tidepooling_windows(station_id, f"{year}0101", f"{year}1231", lat, lon):
                t12 = e.get("low_tide_time_12h", e["low_tide_time"])
                _add_allday(cal,
                    uid=f"tidepool-{station_id}-{e['date']}@tideline",
                    summary=f"🦀 Tidepooling Window — Low: {e['low_height_ft']} ft at {t12}",
                    date_str=e["date"],
                    description=(
                        f"Low tide: {t12} at {e['low_height_ft']} ft\n"
                        f"Sunrise: {e['sunrise']} · Sunset: {e['sunset']}\n"
                        f"Score: {e['score']:.2f} (higher = better)\n"
                        f"Station: {station_name} ({station_id})"
                    ),
                )
                counts["tidepooling"] += 1
        except Exception:
            pass

    # ── slack water ──────────────────────────────────────────────────────────
    if options.get("slack", False):
        try:
            from app.special_events import get_slack_water
            from datetime import date as dt_date
            d_iter = dt_date(year, 1, 1)
            end    = dt_date(year, 12, 31)
            while d_iter <= end:
                date_s = d_iter.isoformat()
                for slack in get_slack_water(station_id, date_s):
                    t = slack["time"]
                    direction = slack["between"].replace("_", " ")
                    uid = f"slack-{station_id}-{date_s}-{t.replace(':', '')}@tideline"
                    dt_ev = datetime.strptime(f"{date_s} {t}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
                    ev = Event()
                    ev.add("uid",     uid)
                    ev.add("summary", f"⚓ Slack Water")
                    ev.add("dtstart", dt_ev)
                    ev.add("dtend",   dt_ev + timedelta(minutes=10))
                    ev.add("description", f"Direction change: {direction}\nStation: {station_name} ({station_id})")
                    cal.add_component(ev)
                    counts["slack_water"] += 1
                d_iter += timedelta(days=1)
        except Exception:
            pass

    # ── radius alerts ────────────────────────────────────────────────────────
    if options.get("radius", False) and lat is not None and lon is not None and radius_miles > 10:
        try:
            from app.alert_engine import find_extreme_in_radius
            from app.station_finder import find_nearest_stations
            events = find_extreme_in_radius(lat, lon, radius_miles, f"{year}0101", f"{year}1231")
            for e in events:
                if e["extreme_type"] != "king_tide":
                    continue
                sid  = e["station_id"]
                snam = e["station_name"]
                dist = e["distance_miles"]
                h    = e["height_ft"]
                _add_allday(cal,
                    uid=f"radius-{sid}-{e['date']}-{e['time'].replace(':','')}@tideline",
                    summary=f"🌊 King Tide Nearby: {snam} ({dist:.0f} mi) — {h} ft",
                    date_str=e["date"],
                    description=(
                        f"Station: {snam} ({sid})\n"
                        f"Distance: {dist:.1f} miles\n"
                        f"Height: {h} ft at {e.get('time_12h', e['time'])}"
                    ),
                )
                counts["radius_alert"] += 1
        except Exception:
            pass

    cal.add_missing_timezones()
    return cal.to_ical(), dict(counts)


def build_alerts_only_ics(
    station_id: str,
    year: int,
    lat: float | None = None,
    lon: float | None = None,
    radius_miles: float = 75.0,
    **kwargs,
) -> tuple[bytes, dict]:
    """Build an alerts-only ICS (all-day events only). Returns (bytes, counts)."""
    return build_tidal_ics(
        station_id, year,
        options={"hilo": False, "alerts": True, "perigean": True,
                 "flood": True, "radius": True},
        lat=lat, lon=lon, radius_miles=radius_miles,
    )
