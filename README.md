# Moon & Tides — Tideline

Tidal calendar for the US coast. Generates ICS calendar files with high/low tides, king tide alerts, tidepooling windows, and Perigean spring tides. Includes a FastAPI web server, a CLI, and an MCP server that lets Claude answer tide questions directly.

Data source: NOAA CO-OPS API (free, no key required, US coastal stations only).

---

## Requirements

- Python 3.11 or later
- Windows, macOS, or Linux

---

## Installation

```powershell
# 1. Clone the repo and enter the directory
git clone <repo-url>
cd Moon_and_Tides

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install the tideline command
pip install -e .
```

After step 3 you can type `tideline` directly in any terminal. If you skip it, prefix every command with `python -m app.cli` instead — they are otherwise identical.

---

## Quick start

```powershell
# What are today's tides near me?
tideline preview "Edmonds WA"

# Download a full-year ICS calendar file
tideline ics "Edmonds WA" --year 2026 --out my_tides.ics
```

Import `my_tides.ics` into Google Calendar, Apple Calendar, or Outlook.

---

## CLI reference

### `tideline preview` — Today's tides

```powershell
tideline preview "Edmonds WA"
tideline preview "San Francisco, CA"
tideline preview --station 9447130
tideline preview --lat 47.81 --lon -122.38
```

Output:
```
Today's tides at 9447130:
  02:06 (2:06 AM)  H  10.32 ft
  09:32 (9:32 AM)  L  -0.87 ft
  17:41 (5:41 PM)  H  10.69 ft
  22:34 (10:34 PM)  L  7.91 ft
```

---

### `tideline tides` — Browse tide predictions

```powershell
# Current year, first 20 events
tideline tides "Edmonds WA"

# Specific year (shows first 20 events)
tideline tides "Edmonds WA" --year 2026

# Single date
tideline tides "Edmonds WA" --date 2026-06-21

# By station ID
tideline tides --station 9447130 --date 2026-06-21

# By coordinates
tideline tides --lat 47.81 --lon -122.38 --date 2026-06-21

# Show more rows
tideline tides "Edmonds WA" --year 2026 --count 100
```

Times are shown in both 24-hour and 12-hour AM/PM format.

---

### `tideline ics` — Download a calendar file

```powershell
# Full year ICS (saves to tides_STATIONID_YEAR.ics in current folder)
tideline ics "Edmonds WA" --year 2026

# Specify output filename
tideline ics "Edmonds WA" --year 2026 --out my_tides_2026.ics

# King tide / extreme event alerts only (all-day events, good for overlaying)
tideline ics "Edmonds WA" --year 2026 --alerts-only --out alerts_2026.ics

# By station ID
tideline ics --station 9447130 --year 2026 --out seattle_2026.ics

# By coordinates
tideline ics --lat 47.81 --lon -122.38 --year 2026 --out tides.ics
```

The ICS file contains one event per high/low tide with the height, datum, station name, and next tide in the description. Import it into any calendar app that accepts `.ics` files.

---

### `tideline stations` — Find nearby NOAA stations

```powershell
# Stations within 50 miles (default)
tideline stations "Edmonds WA"

# Custom radius
tideline stations "Edmonds WA" --radius 100

# Limit number of results
tideline stations "Edmonds WA" --radius 50 --count 3
```

Output:
```
Location: Edmonds, Snohomish County, Washington, United States

ID         Name                           Miles    Harmonic
------------------------------------------------------------
9447130    Seattle                        14.5    yes
9445958    Bremerton                      20.6    yes
9444900    Port Townsend                  27.3    yes
```

"Harmonic" means the station has full tidal harmonic data (required for slack water and tidepooling features).

---

### `tideline extremes` — Highest and lowest tides of the year

```powershell
tideline extremes "Edmonds WA" --year 2026
tideline extremes --station 9447130 --year 2026
```

Output:
```
Top 10 Highest Tides:
  2026-01-05 07:07 (7:07 AM)  13.01 ft
  ...

Top 10 Lowest Tides:
  2026-06-15 11:33 (11:33 AM)  -4.30 ft
  ...
```

---

## Web API

Start the server:

```powershell
python -m uvicorn app.main:app --reload
```

Then open `http://localhost:8000/docs` for the interactive API explorer.

Key endpoints:

| Endpoint | Description |
|---|---|
| `POST /geocode` | Convert address to lat/lon |
| `GET /api/v1/stations/nearest?lat=&lon=&count=5` | Nearest NOAA stations |
| `GET /api/v1/stations/radius?lat=&lon=&radius_miles=50` | Stations within radius |
| `GET /api/v1/station/{id}` | Station metadata + tidal range |
| `GET /api/v1/tides/day?station_id=&date=YYYY-MM-DD` | Tides for one day |
| `GET /api/v1/tides/range?station_id=&begin=&end=` | Tides for a date range |
| `GET /api/v1/tides/year-summary?station_id=&year=` | Monthly means + extremes |
| `GET /calendar/2026/47.81,-122.38.ics` | Download ICS via URL |
| `GET /calendar/2026/47.81,-122.38-alerts.ics` | Alerts-only ICS via URL |

---

## MCP server (for Claude Desktop)

The MCP server lets Claude answer tide questions using live NOAA data.

Add this to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tideline": {
      "command": "python",
      "args": ["C:\\full\\path\\to\\Moon_and_Tides\\mcp_server.py"]
    }
  }
}
```

Then in Claude you can ask things like:
- "When is high tide in Seattle tomorrow?"
- "Find the lowest tide within 50 miles of San Francisco in July 2026"
- "What are the best tidepooling days near Bodega Bay this summer?"
- "Generate a calendar link for tides near Edmonds WA for 2026"

Available MCP tools: `geocode`, `find_stations`, `get_tides_day`, `get_tides_range`, `get_station_info`, `get_tidal_type`, `get_extreme_tides`, `find_extreme_in_radius`, `check_flood_risk`, `get_slack_water`, `get_tidepooling_windows`, `get_perigean_spring_tides`, `generate_ics_url`.

---

## Caching

All NOAA data is cached locally in `cache/tides.db` (SQLite):

- Tide predictions: 30-day cache lifetime per station/year
- Station list: 7-day cache lifetime
- Tidal ranges and Perigean events: cached indefinitely until recomputed

The cache means repeat commands are instant and tests never hit the network. Delete `cache/tides.db` to force a fresh fetch.

---

## Running tests

```powershell
# All fast tests (no network)
python -m pytest tests/ -m "not live and not slow" -v

# Tests that hit the real NOAA API
python -m pytest tests/ -m "live" -v
```

---

## Imported events into the wrong Google Calendar?

If you accidentally import the `.ics` file into the wrong Google Calendar, use the included cleanup script to delete all tide events without having to remove them one by one.

**The script:** `scripts/delete_tide_events.gs`

**Steps:**

1. Go to [script.google.com](https://script.google.com) and click **New project**
2. Delete any existing code and paste the entire contents of `scripts/delete_tide_events.gs`
3. Set `CALENDAR_NAME` to the exact name of the calendar you imported into (find it in the left sidebar of Google Calendar)
4. Leave `DRY_RUN = true` for now
5. Click **Save**, then **Run** — select `deleteTideEvents` in the dropdown
6. On first run, approve the permissions Google asks for
7. Check the **Execution log** at the bottom — it will list all tide events it *would* delete
8. If the list looks right, change `DRY_RUN = false` and run again to actually delete
9. If you hit Google's rate limits, just run again — the script tracks progress and picks up where it left off

The script deletes events matching these title patterns:
- `🌊 High Tide —`
- `🏖 Low Tide —`
- `⚠️ King Tide —`
- `⚠️ Extreme Low —`

It will not touch any other events in the calendar.

---

## Project structure

```
app/
  tide_data.py       — NOAA fetch + SQLite cache
  station_finder.py  — Station search, haversine distance
  ics_builder.py     — RFC-5545 ICS generation
  alert_engine.py    — King tide / flood risk detection
  special_events.py  — Slack water, tidepooling, Perigean tides
  geocode.py         — Nominatim address lookup
  cli.py             — tideline command
  main.py            — FastAPI web server
mcp_server.py        — MCP server for Claude Desktop
scripts/
  delete_tide_events.gs  — Google Apps Script to remove imported tide events
tests/               — 44 tests, all passing
cache/               — SQLite cache (gitignored)
```

---

## Notes

- Coverage is US coastal stations only (NOAA CO-OPS network).
- Tidal heights are relative to MLLW (Mean Lower Low Water) by default.
- Times are shown in local standard/daylight time for the station's location.
- The `tideline` command is available after `pip install -e .`. Without it, use `python -m app.cli` as a drop-in replacement for every example above.
- No NOAA station exists at every address — the app always uses the nearest available station and tells you the distance. For Edmonds WA, that's Seattle (#9447130, ~14 miles).
