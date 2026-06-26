import argparse
import sys
from datetime import datetime

# Windows terminals default to cp1252 which can't render emoji.
# Reconfigure stdout to UTF-8 so the count table prints cleanly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _resolve_station(args) -> str:
    if hasattr(args, "station") and args.station:
        return args.station
    if hasattr(args, "lat") and args.lat is not None and args.lon is not None:
        from app.station_finder import find_nearest_stations
        stations = find_nearest_stations(args.lat, args.lon, max_results=1)
        if not stations:
            print(f"No stations found near ({args.lat}, {args.lon})", file=sys.stderr)
            sys.exit(1)
        return stations[0]["id"]
    # geocode address
    location = getattr(args, "location", None)
    if not location:
        print("Must provide location, --station, or --lat/--lon", file=sys.stderr)
        sys.exit(1)
    from app.geocode import geocode_address
    results = geocode_address(location)
    if not results:
        print(f"Could not geocode: {location}", file=sys.stderr)
        sys.exit(1)
    lat, lon = results[0]["lat"], results[0]["lon"]
    from app.station_finder import find_nearest_stations
    stations = find_nearest_stations(lat, lon, max_results=1)
    if not stations:
        print(f"No NOAA stations found near {location}", file=sys.stderr)
        sys.exit(1)
    s = stations[0]
    # Warn when the station name doesn't match what was searched
    searched_first_word = location.split()[0].lower()
    if searched_first_word not in s["name"].lower():
        print(f"Note: No NOAA station at '{location}'. "
              f"Using nearest: {s['name']} ({s['distance_miles']:.1f} mi away, #{s['id']})")
    return s["id"]


def cmd_tides(args):
    station_id = _resolve_station(args)
    year = getattr(args, "year", None) or datetime.now().year
    date = getattr(args, "date", None)

    from app.tide_data import get_hilo_predictions
    if date:
        d = datetime.strptime(date, "%Y-%m-%d")
        begin = d.strftime("%Y%m%d")
        end = d.strftime("%Y%m%d")
    else:
        begin = f"{year}0101"
        end = f"{year}1231"

    count = getattr(args, "count", 20)
    data = get_hilo_predictions(station_id, begin, end)
    print(f"Station: {station_id}  |  {len(data)} tide events")
    print(f"{'Date':<12} {'Time':<22} {'Type':<5} {'Height (ft)'}")
    print("-" * 56)
    for item in data[:count]:
        t = f"{item['time']} ({item['time_12h']})"
        print(f"{item['date']:<12} {t:<22} {item['type']:<5} {item['height_ft']:.2f}")
    if len(data) > count:
        print(f"... and {len(data) - count} more  (use --count N to show more)")
    print("\nTip: use 'tideline ics' to download a calendar file.")


def cmd_stations(args):
    location = getattr(args, "location", None)
    radius = getattr(args, "radius", 50.0)
    count = getattr(args, "count", 5)

    from app.geocode import geocode_address
    results = geocode_address(location)
    if not results:
        print(f"Could not geocode: {location}", file=sys.stderr)
        sys.exit(1)
    lat, lon = results[0]["lat"], results[0]["lon"]
    print(f"Location: {results[0]['display_name']}")
    print(f"Lat: {lat}, Lon: {lon}\n")

    if radius:
        from app.station_finder import find_stations_in_radius
        stations = find_stations_in_radius(lat, lon, radius)
    else:
        from app.station_finder import find_nearest_stations
        stations = find_nearest_stations(lat, lon, max_results=count)

    print(f"{'ID':<10} {'Name':<30} {'Miles':<8} {'Harmonic'}")
    print("-" * 60)
    for s in stations[:count]:
        h = "yes" if s.get("harmonic") else "no"
        print(f"{s['id']:<10} {s['name']:<30} {s['distance_miles']:.1f}    {h}")


def _print_counts(counts: dict) -> None:
    LABELS = {
        "hilo_high":    "🌊 High tides",
        "hilo_low":     "🏖 Low tides",
        "king_tide":    "⚠️  King tides",
        "extreme_low":  "⚠️  Extreme lows",
        "perigean":     "🌕 Perigean spring tides",
        "flood_risk":   "🚨 Flood risk days",
        "tidepooling":  "🦀 Tidepooling windows",
        "slack_water":  "⚓ Slack water events",
        "radius_alert": "🌊 Nearby radius alerts",
    }
    print("\nEvents included:")
    for key, label in LABELS.items():
        n = counts.get(key, 0)
        if n:
            print(f"  {label:<32} {n:>4}")
    print(f"  {'Total':<32} {sum(counts.values()):>4}")


def cmd_ics(args):
    station_id = _resolve_station(args)
    year = getattr(args, "year", None) or datetime.now().year
    out = getattr(args, "out", None)
    alerts_only = getattr(args, "alerts_only", False)
    radius = getattr(args, "radius", 0.0) or 0.0

    # Resolve lat/lon for features that need them
    lat, lon = None, None
    if hasattr(args, "lat") and args.lat is not None:
        lat, lon = args.lat, args.lon
    elif getattr(args, "location", None):
        from app.geocode import geocode_address
        geo = geocode_address(args.location)
        if geo:
            lat, lon = geo[0]["lat"], geo[0]["lon"]

    from app.ics_builder import build_tidal_ics, build_alerts_only_ics
    if alerts_only:
        ics_bytes, counts = build_alerts_only_ics(station_id, year, lat=lat, lon=lon)
    else:
        options = {
            "hilo":       True,
            "alerts":     True,
            "perigean":   True,
            "flood":      True,
            "tidepooling": lat is not None,
            "slack":      False,  # requires curve data per day; slow
            "radius":     radius > 10 and lat is not None,
        }
        ics_bytes, counts = build_tidal_ics(station_id, year, options=options, lat=lat, lon=lon, radius_miles=radius)

    fname = out or f"tides_{station_id}_{year}.ics"
    with open(fname, "wb") as f:
        f.write(ics_bytes)
    print(f"Saved {len(ics_bytes):,} bytes to {fname}")
    _print_counts(counts)


def cmd_extremes(args):
    station_id = _resolve_station(args)
    year = getattr(args, "year", None) or datetime.now().year

    from app.tide_data import get_hilo_predictions
    data = get_hilo_predictions(station_id, f"{year}0101", f"{year}1231")
    highs = sorted([d for d in data if d["type"] == "H"], key=lambda x: x["height_ft"], reverse=True)
    lows = sorted([d for d in data if d["type"] == "L"], key=lambda x: x["height_ft"])

    print(f"Station: {station_id}  |  Year: {year}")
    print("\nTop 10 Highest Tides:")
    for item in highs[:10]:
        print(f"  {item['date']} {item['time']} ({item['time_12h']})  {item['height_ft']:.2f} ft")
    print("\nTop 10 Lowest Tides:")
    for item in lows[:10]:
        print(f"  {item['date']} {item['time']} ({item['time_12h']})  {item['height_ft']:.2f} ft")


def cmd_preview(args):
    station_id = _resolve_station(args)
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    from app.tide_data import get_hilo_predictions
    data = get_hilo_predictions(station_id, today, today)
    print(f"Today's tides at {station_id}:")
    for item in data:
        print(f"  {item['time']} ({item['time_12h']})  {item['type']}  {item['height_ft']:.2f} ft")


def main():
    parser = argparse.ArgumentParser(prog="tideline", description="Moon & Tides CLI")
    sub = parser.add_subparsers(dest="command")

    # tides
    p_tides = sub.add_parser("tides", help="Show tide predictions (use 'ics' to download a calendar file)")
    p_tides.add_argument("location", nargs="?")
    p_tides.add_argument("--station")
    p_tides.add_argument("--lat", type=float)
    p_tides.add_argument("--lon", type=float)
    p_tides.add_argument("--year", type=int)
    p_tides.add_argument("--date")
    p_tides.add_argument("--count", type=int, default=20, help="Number of events to display")

    # stations
    p_stations = sub.add_parser("stations")
    p_stations.add_argument("location")
    p_stations.add_argument("--radius", type=float, default=50.0)
    p_stations.add_argument("--count", type=int, default=5)

    # ics
    p_ics = sub.add_parser("ics")
    p_ics.add_argument("location", nargs="?")
    p_ics.add_argument("--station")
    p_ics.add_argument("--lat", type=float)
    p_ics.add_argument("--lon", type=float)
    p_ics.add_argument("--year", type=int)
    p_ics.add_argument("--out")
    p_ics.add_argument("--alerts-only", action="store_true")
    p_ics.add_argument("--radius", type=float, default=0.0)

    # extremes
    p_ext = sub.add_parser("extremes")
    p_ext.add_argument("location", nargs="?")
    p_ext.add_argument("--station")
    p_ext.add_argument("--lat", type=float)
    p_ext.add_argument("--lon", type=float)
    p_ext.add_argument("--year", type=int)
    p_ext.add_argument("--radius", type=float)

    # preview
    p_prev = sub.add_parser("preview")
    p_prev.add_argument("location", nargs="?")
    p_prev.add_argument("--station")
    p_prev.add_argument("--lat", type=float)
    p_prev.add_argument("--lon", type=float)

    args = parser.parse_args()
    dispatch = {
        "tides": cmd_tides,
        "stations": cmd_stations,
        "ics": cmd_ics,
        "extremes": cmd_extremes,
        "preview": cmd_preview,
    }
    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
