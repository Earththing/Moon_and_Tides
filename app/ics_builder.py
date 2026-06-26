from datetime import date, datetime, timedelta

from icalendar import Calendar, Event, Timezone, TimezoneStandard, vText

from app.tide_data import get_hilo_predictions, get_station_tidal_range


def _station_name(station_id: str) -> str:
    try:
        from app.station_finder import get_all_stations
        stations = get_all_stations()
        for s in stations:
            if s["id"] == station_id:
                return s["name"]
    except Exception:
        pass
    return station_id


def _make_uid(station_id: str, date_str: str, time_str: str, tide_type: str) -> str:
    hhmm = time_str.replace(":", "")
    return f"tide-{station_id}-{date_str}-{hhmm}-{tide_type}@tideline"


def _ft_to_m(ft: float) -> float:
    return round(ft * 0.3048, 2)


def _build_calendar(station_id: str, year: int) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//Tideline//Moon and Tides//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", f"Tides — {station_id} {year}")

    # Add a minimal VTIMEZONE for UTC
    tz = Timezone()
    tz.add("tzid", "UTC")
    tzstd = TimezoneStandard()
    tzstd.add("dtstart", datetime(1970, 1, 1))
    tzstd.add("tzoffsetfrom", timedelta(0))
    tzstd.add("tzoffsetto", timedelta(0))
    tzstd.add("tzname", "UTC")
    tz.add_component(tzstd)
    cal.add_component(tz)

    return cal


def _extreme_thresholds(station_id: str, year: int) -> tuple[float, float]:
    data = get_hilo_predictions(station_id, f"{year}0101", f"{year}1231")
    highs = sorted(d["height_ft"] for d in data if d["type"] == "H")
    lows = sorted(d["height_ft"] for d in data if d["type"] == "L")
    if not highs or not lows:
        return (999.0, -999.0)
    high_thresh = highs[int(len(highs) * 0.90)]
    low_thresh = lows[int(len(lows) * 0.10)]
    return high_thresh, low_thresh


def build_tidal_ics(
    station_id: str,
    year: int,
    options: dict | None = None,
) -> bytes:
    if options is None:
        options = {"hilo": True}

    cal = _build_calendar(station_id, year)
    station_name = _station_name(station_id)
    data = get_hilo_predictions(station_id, f"{year}0101", f"{year}1231")

    # Build lookup for next tide
    next_tide: dict[int, dict] = {}
    for i in range(len(data) - 1):
        next_tide[i] = data[i + 1]

    high_thresh, low_thresh = _extreme_thresholds(station_id, year)

    for i, item in enumerate(data):
        h = item["height_ft"]
        h_m = _ft_to_m(h)
        tide_type = item["type"]
        date_str = item["date"]
        time_str = item["time"]

        dt_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        d = date.fromisoformat(date_str)

        # All-day extreme event
        is_extreme_high = tide_type == "H" and h >= high_thresh
        is_extreme_low = tide_type == "L" and h <= low_thresh

        if is_extreme_high:
            ev = Event()
            ev.add("uid", _make_uid(station_id, date_str, time_str, "EH"))
            ev.add("summary", f"⚠️ King Tide — {h} ft")
            ev.add("dtstart", d)
            ev.add("dtend", d + timedelta(days=1))
            cal.add_component(ev)

        elif is_extreme_low:
            ev = Event()
            ev.add("uid", _make_uid(station_id, date_str, time_str, "EL"))
            ev.add("summary", f"⚠️ Extreme Low — {h} ft")
            ev.add("dtstart", d)
            ev.add("dtend", d + timedelta(days=1))
            cal.add_component(ev)

        # Regular hilo event
        if options.get("hilo", True):
            nxt = next_tide.get(i)
            if nxt:
                nxt_label = "low" if tide_type == "H" else "high"
                nxt_time = f"{nxt['time']} ({nxt['time_12h']})" if "time_12h" in nxt else nxt["time"]
                desc = (
                    f"Height: {h} ft ({h_m} m)\n"
                    f"Datum: MLLW\n"
                    f"Station: {station_name} ({station_id})\n"
                    f"Next {nxt_label} tide: {nxt_time} — {nxt['height_ft']} ft"
                )
            else:
                desc = (
                    f"Height: {h} ft ({h_m} m)\n"
                    f"Datum: MLLW\n"
                    f"Station: {station_name} ({station_id})"
                )

            if tide_type == "H":
                summary = f"🌊 High Tide — {h} ft"
                duration = timedelta(minutes=15)
            else:
                summary = f"🏖 Low Tide — {h} ft"
                duration = timedelta(minutes=15)

            ev = Event()
            ev.add("uid", _make_uid(station_id, date_str, time_str, tide_type))
            ev.add("summary", summary)
            ev.add("dtstart", dt_naive)
            ev.add("dtend", dt_naive + duration)
            ev.add("description", desc)
            cal.add_component(ev)

    return cal.to_ical()


def build_alerts_only_ics(station_id: str, year: int, **kwargs) -> bytes:
    cal = _build_calendar(station_id, year)
    station_name = _station_name(station_id)
    data = get_hilo_predictions(station_id, f"{year}0101", f"{year}1231")

    high_thresh, low_thresh = _extreme_thresholds(station_id, year)

    for item in data:
        h = item["height_ft"]
        tide_type = item["type"]
        date_str = item["date"]
        time_str = item["time"]
        d = date.fromisoformat(date_str)

        is_extreme_high = tide_type == "H" and h >= high_thresh
        is_extreme_low = tide_type == "L" and h <= low_thresh

        if is_extreme_high:
            ev = Event()
            ev.add("uid", _make_uid(station_id, date_str, time_str, "EH"))
            ev.add("summary", f"⚠️ King Tide — {h} ft")
            ev.add("dtstart", d)
            ev.add("dtend", d + timedelta(days=1))
            cal.add_component(ev)

        elif is_extreme_low:
            ev = Event()
            ev.add("uid", _make_uid(station_id, date_str, time_str, "EL"))
            ev.add("summary", f"⚠️ Extreme Low — {h} ft")
            ev.add("dtstart", d)
            ev.add("dtend", d + timedelta(days=1))
            cal.add_component(ev)

    return cal.to_ical()
