# Moon & Tides — Tideline

Tidal calendar for the US coast. Generates ICS calendar files with high/low tides, king tide alerts, tidepooling windows, flood risk events, Perigean spring tides, and more. Comes with a web dashboard, a CLI, and an MCP server so Claude can answer tide questions directly.

Data source: NOAA CO-OPS API — free, no account or API key required. US coastal stations only.

---

## Requirements

- **Python 3.11 or later** — for the backend, CLI, and MCP server
- **Node.js 18 or later** — for the web dashboard (optional if you only use the CLI)
- Windows, macOS, or Linux

---

## Installation

### Step 1 — Get the code

```powershell
git clone https://github.com/Earththing/Moon_and_Tides.git
cd Moon_and_Tides
```

### Step 2 — Install Python dependencies

```powershell
pip install -r requirements.txt
```

This installs FastAPI, httpx, ephem (for sunrise/sunset), icalendar, the MCP SDK, and everything else the backend needs.

### Step 3 — Register the `tideline` command

```powershell
pip install -e .
```

This makes `tideline` available as a command in your terminal. If you skip this step, replace every `tideline` command below with `python -m app.cli` — they are otherwise identical.

### Step 4 (optional) — Install the web dashboard

```powershell
cd frontend
npm install
cd ..
```

This downloads the React/TypeScript frontend dependencies (~150 MB in `node_modules`). Skip if you only plan to use the CLI or API.

---

## Getting the app running

The app has two parts: a **backend** (Python/FastAPI) that handles all data fetching, caching, and ICS generation, and a **frontend** (React) that provides the interactive dashboard. You need both running to use the web interface.

### Terminal 1 — Start the backend

```powershell
python -m uvicorn app.main:app --reload
```

**What this does:** starts the FastAPI data server on port 8000. It handles all communication with NOAA, builds ICS calendar files, computes sunrise/sunset times, and serves the REST API that the frontend calls. The `--reload` flag means it automatically restarts when you change a Python file — you never need to stop and restart it manually during development.

You'll see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

You can verify it's working at `http://localhost:8000/docs` — that's the interactive API explorer.

### Terminal 2 — Start the frontend

```powershell
cd frontend
npm run dev
```

**What this does:** starts the Vite development server on port 5173. Vite serves the React dashboard and also acts as a proxy — when the dashboard calls `/api/v1/...` or `/calendar/...`, Vite forwards those requests to the backend on port 8000. This means you only ever need to open one URL in your browser.

You'll see:
```
  VITE v8.x  ready in 300ms
  ➜  Local:   http://localhost:5173/
```

### Step 3 — Open the dashboard

Go to **http://localhost:5173** in your browser.

Search for a city or address, and the dashboard will find the nearest NOAA tide station and show today's tide curve, nearby stations, upcoming events, and a calendar download button.

---

## Quick start — CLI only

If you just want tide data without the web interface:

```powershell
# Today's tides near you (fastest way to check)
tideline preview "Seattle WA"

# Download a full-year calendar file
tideline ics "Seattle WA" --year 2026 --out seattle_tides_2026.ics
```

Import the `.ics` file into Google Calendar, Apple Calendar, or Outlook.

---

## CLI reference

All commands accept a place name, a station ID, or coordinates. If no NOAA station exists at the location you search, the nearest one is used automatically and you'll be told how far away it is.

### `tideline preview` — Today's tides at a glance

```powershell
tideline preview "Seattle WA"
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

### `tideline tides` — Browse predictions

```powershell
# Today's tides (first 20 events)
tideline tides "Seattle WA"

# Specific year — shows first 20 events
tideline tides "Seattle WA" --year 2026

# Single date
tideline tides "Seattle WA" --date 2026-06-21

# By station ID
tideline tides --station 9447130 --date 2026-06-21

# By coordinates
tideline tides --lat 47.81 --lon -122.38 --date 2026-06-21

# Show more rows (default is 20)
tideline tides "Seattle WA" --year 2026 --count 100
```

Times are shown in both 24-hour and 12-hour AM/PM format. Use `tideline ics` (below) to save a full year as a calendar file.

---

### `tideline ics` — Generate a calendar file

```powershell
# Full year, saves to tides_9447130_2026.ics in current folder
tideline ics "Seattle WA" --year 2026

# Choose the output filename
tideline ics "Seattle WA" --year 2026 --out seattle_2026.ics

# Alerts only — all-day events for king tides, extremes, Perigean tides
# Good for overlaying on top of a main calendar without clutter
tideline ics "Seattle WA" --year 2026 --alerts-only --out alerts_2026.ics

# By station ID
tideline ics --station 9447130 --year 2026 --out seattle_2026.ics

# By coordinates
tideline ics --lat 47.81 --lon -122.38 --year 2026 --out tides.ics
```

After saving, the command shows a breakdown of what's in the file:

```
Saved 432,817 bytes to seattle_2026.ics

Events included:
  🌊 High tides                    1410
  🏖 Low tides                     1410
  ⚠️  King tides                     52
  ⚠️  Extreme lows                   52
  🌕 Perigean spring tides            6
  🚨 Flood risk days                  0
  🦀 Tidepooling windows            124
  Total                            3054
```

**Event types in the ICS file:**

| Icon | Event | Type | When |
|---|---|---|---|
| 🌊 | High Tide | Timed (15 min) | Every high tide |
| 🏖 | Low Tide | Timed (15 min) | Every low tide |
| ⚠️ | King Tide | All-day | Top 10% of highs |
| ⚠️ | Extreme Low | All-day | Bottom 10% of lows |
| 🌕 | Perigean Spring Tide | All-day | Moon at perigee + new/full moon |
| 🚨 | Flood Risk | All-day | Predicted high exceeds NOAA flood threshold |
| 🦀 | Tidepooling Window | All-day | Low tide during daylight hours |
| ⚓ | Slack Water | Timed (10 min) | Tide reversal (harmonic stations only) |
| 🌊 | King Tide Nearby | All-day | King tide at a station within your radius |

---

### `tideline stations` — Find NOAA stations near you

```powershell
# All stations within 50 miles (default)
tideline stations "Seattle WA"

# Wider search
tideline stations "Seattle WA" --radius 100

# Limit results
tideline stations "Seattle WA" --radius 50 --count 3
```

Output:
```
Location: Seattle, King County, Washington, United States

ID         Name                           Miles    Harmonic
------------------------------------------------------------
9447130    Seattle                         0.4    yes
9445958    Bremerton                      13.9    yes
9444900    Port Townsend                  27.3    yes
9446484    Tacoma                         23.8    yes
```

**Harmonic** stations have full tidal constituent data. Tidepooling windows and slack water events require a harmonic station.

---

### `tideline extremes` — Highest and lowest tides of the year

```powershell
tideline extremes "Seattle WA" --year 2026
tideline extremes --station 9447130 --year 2026
```

Output:
```
Station: 9447130  |  Year: 2026

Top 10 Highest Tides:
  2026-01-05 07:07 (7:07 AM)  13.01 ft
  2026-12-26 07:22 (7:22 AM)  13.01 ft
  ...

Top 10 Lowest Tides:
  2026-06-15 11:33 (11:33 AM)  -4.30 ft
  2026-06-16 12:22 (12:22 PM)  -4.20 ft
  ...
```

---

## Web dashboard

The web dashboard at `http://localhost:5173` gives you an interactive view of all the same data.

### Features

**Location search** — type any city, address, or landmark. The app geocodes it and finds the nearest NOAA station. If no station exists at your exact location, a banner tells you which station is being used and how far away it is.

**Tide curve chart** — shows the tidal pattern for the selected date with:
- 24-hour and 12-hour times on hover
- Colored dots for high (blue) and low (green) tides with height labels
- A "now" line showing the current time (day view only)
- Flood threshold line if NOAA has one for the station
- Day/night shading (toggle with the 🌙 button) — night hours are shaded dark blue with a gradual dawn/dusk transition showing sunrise and sunset times

**Four chart views** — select with the Day / Week / Month / Year buttons (hover each for a description):
- **Day** — 6-minute tide curve for a single day
- **Week** — high & low tides across 7 days (use ← → to navigate weeks)
- **Month** — high & low tides for the full month
- **Year** — monthly average high & low bars

**Date navigation** — ← and → arrows move by one day/week/month/year depending on the view. The date picker jumps to a specific date. A **Today** button appears when you're not on today.

**Nearby stations panel** — lists the 5 nearest NOAA stations with live tide badges showing current height and direction. Click any station to switch to it.

**Today's tides list** — the current tide event is highlighted. Shows times in 12-hour format.

**Calendar options** — choose which event types to include in the downloaded ICS. Options disabled for your station (e.g. slack water on a non-harmonic station) show a tooltip explaining why.

**Download button** — shows the total event count before you download. Expand "Show event breakdown" to see counts by type.

**Coming up feed** — upcoming events in the next 30 days: king tides (amber), tidepooling windows (green), and Perigean spring tides. Shows up to 6; click "View all" to see the full list on the Alerts page.

**Alerts page** — full list of all upcoming events for the selected station and year. Also reachable from the Alerts tab in the nav bar — it remembers your last station.

---

## Web API

The backend exposes a REST API at `http://localhost:8000`. Open `http://localhost:8000/docs` for an interactive explorer where you can try any endpoint.

| Endpoint | What it does |
|---|---|
| `POST /geocode` | Convert address → lat/lon |
| `GET /api/v1/stations/nearest?lat=&lon=&count=5` | Nearest NOAA stations with distance |
| `GET /api/v1/stations/radius?lat=&lon=&radius_miles=50` | All stations within a radius |
| `GET /api/v1/station/{id}` | Station metadata, tidal range, flood thresholds |
| `GET /api/v1/tides/day?station_id=&date=YYYY-MM-DD` | 6-min curve + hilo for one day |
| `GET /api/v1/tides/range?station_id=&begin=&end=` | Hilo data for a date range |
| `GET /api/v1/tides/year-summary?station_id=&year=` | Monthly means and extremes |
| `GET /api/v1/special-events?station_id=&year=` | King tides, Perigean tides, flood risk, tidepooling |
| `GET /api/v1/solar-day?lat=&lon=&date=` | Sunrise/sunset in local time |
| `GET /api/v1/solar-range?lat=&lon=&begin=&end=` | Sunrise/sunset for a date range |
| `GET /api/v1/ics-preview?station_id=&year=&options=` | Event counts without building the file |
| `GET /calendar/2026/47.81,-122.38.ics?options=hilo,alerts` | Download ICS by coordinates |
| `GET /calendar/2026/47.81,-122.38-alerts.ics` | Alerts-only ICS by coordinates |

**Example — try this in your browser while the backend is running:**
```
http://localhost:8000/api/v1/tides/day?station_id=9447130&date=2026-07-04
http://localhost:8000/api/v1/solar-day?lat=47.81&lon=-122.38&date=2026-07-04
http://localhost:8000/api/v1/special-events?station_id=9447130&year=2026
```

---

## MCP server (for Claude Desktop)

The MCP server lets Claude answer tide questions by calling real NOAA data directly. Once configured, you can ask Claude things like:

- "When is high tide in Seattle tomorrow?"
- "What are the best tidepooling days near Bodega Bay this summer?"
- "Find the lowest tide within 50 miles of San Francisco in July 2026"
- "Are there any king tides in Puget Sound this month?"

### Setup

Find your Claude Desktop config file:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this (replace the path with your actual path):

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

On macOS/Linux use forward slashes:
```json
{
  "mcpServers": {
    "tideline": {
      "command": "python",
      "args": ["/full/path/to/Moon_and_Tides/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop after saving. The MCP server starts automatically when Claude opens — you do not need to run it yourself.

### Available tools

| Tool | What you can ask |
|---|---|
| `geocode` | Find lat/lon for an address |
| `find_stations` | "What NOAA stations are near Portland OR?" |
| `get_tides_day` | "What are today's tides in Bodega Bay?" |
| `get_tides_range` | "Show me tides for the week of July 4th in Seattle" |
| `get_station_info` | "What's the tidal range at station 9447130?" |
| `get_tidal_type` | "Is Astoria OR diurnal or semidiurnal?" |
| `get_extreme_tides` | "What's the highest tide in Seattle this summer?" |
| `find_extreme_in_radius` | "Find king tides within 75 miles of San Francisco in January" |
| `check_flood_risk` | "Any flood risk tides in Miami this winter?" |
| `get_slack_water` | "When is slack water in Puget Sound on June 21?" |
| `get_tidepooling_windows` | "Best tidepooling days near Monterey in July?" |
| `get_perigean_spring_tides` | "When are the Perigean spring tides in 2026?" |
| `generate_ics_url` | "Give me a calendar link for Seattle tides 2026" |

---

## Caching

All data is cached locally in `cache/tides.db` (SQLite, created automatically). The cache keeps data indefinitely and only re-fetches when something is likely to have changed.

| Data | Kept | Re-fetched when |
|---|---|---|
| Tide predictions — past years | Forever | Never (NOAA doesn't revise completed years) |
| Tide predictions — current/future year | Forever | Once a year (harmonic constants may be updated) |
| Station list | Forever | Every 30 days (new stations added occasionally) |
| Tidal ranges | Forever | Only if manually deleted |
| Flood level thresholds | Forever | Only if manually deleted |
| Perigean spring tide dates | Forever | Astronomical — one computation per year |
| Sunrise/sunset times | Forever | Astronomical — never changes for a given date |

The cache is fully transparent — repeat commands are instant and tests never hit the network. To force a full refresh, delete `cache/tides.db`.

---

## Running tests

```powershell
# Fast tests — no network required, runs in ~5 seconds
python -m pytest tests/ -m "not live and not slow" -v

# Tests that hit the real NOAA API (requires internet)
python -m pytest tests/ -m "live" -v

# Frontend tests
cd frontend
npm test
```

Current counts: 45 Python tests, 21 TypeScript tests, all passing.

---

## Importing your tides calendar

### Google Calendar

1. Go to calendar.google.com → Settings (gear icon) → **Import & export**
2. Click **Import**, select your `.ics` file, choose which calendar to add it to
3. Click **Import**

For a live-updating subscription instead of a one-time import, use the calendar URL:
```
http://localhost:8000/calendar/2026/47.81,-122.38.ics?options=hilo,alerts,perigean
```
In Google Calendar: **Other calendars → From URL**, paste the link.

### Apple Calendar

- **One-time import:** File → Import, select the `.ics` file
- **Subscribe (updates automatically):** File → New Calendar Subscription, paste the URL above

### Outlook

File → Open & Export → Import/Export → Import an iCalendar file.

---

## Imported events into the wrong Google Calendar?

If you added the `.ics` to the wrong calendar and want to remove all tide events:

**The script:** `scripts/delete_tide_events.gs`

**Steps:**

1. Go to [script.google.com](https://script.google.com) and click **New project**
2. Delete any existing code and paste the entire contents of `scripts/delete_tide_events.gs`
3. Set `CALENDAR_NAME` at the top to the exact name of the calendar you imported into (find it in the left sidebar of Google Calendar)
4. Leave `DRY_RUN = true` for now
5. Click **Save**, then **Run** — select `deleteTideEvents` in the dropdown
6. On first run, approve the permissions Google asks for
7. Check the **Execution log** at the bottom — it lists everything it *would* delete
8. When satisfied, change `DRY_RUN = false` and run again to actually delete
9. If you hit Google's rate limits mid-run, just run again — it resumes where it left off

The script removes all event types that Tideline creates:

| Title prefix | Event type |
|---|---|
| `🌊 High Tide` | High tide events |
| `🏖 Low Tide` | Low tide events |
| `⚠️ King Tide` | King tide alerts |
| `⚠️ Extreme Low` | Extreme low tide alerts |
| `🌕 Perigean Spring Tide` | Perigean events |
| `🚨 Flood Risk` | Flood risk events |
| `🦀 Tidepooling Window` | Tidepooling windows |
| `⚓ Slack Water` | Slack water events |
| `🌊 King Tide Nearby` | Radius alerts |

It will not touch any other events in the calendar.

---

## Project structure

```
app/
  tide_data.py       — NOAA fetch + SQLite cache + to_12h() helper
  station_finder.py  — Station search, haversine distance, tidal type
  ics_builder.py     — RFC-5545 ICS: all 9 event types, returns event counts
  alert_engine.py    — Extreme tide detection, flood risk, radius sweep
  special_events.py  — Slack water, tidepooling windows, Perigean tides
  solar_cache.py     — Sunrise/sunset via ephem, cached in SQLite
  geocode.py         — Nominatim address → lat/lon
  cli.py             — tideline CLI (preview/tides/ics/stations/extremes)
  main.py            — FastAPI web server + all REST endpoints

mcp_server.py        — MCP server for Claude Desktop (13 tools)

frontend/
  src/
    pages/
      Dashboard.tsx  — Main dashboard (chart, stations, tides, feed)
      AlertsPage.tsx — Full upcoming events list
      HelpPage.tsx   — Calendar import instructions
      MapPage.tsx    — Station map (stub — see TODO.md)
    components/
      TideCurveChart.tsx   — Day/week/month/year chart with day/night shading
      DateNav.tsx          — Date navigation + day/night toggle
      NearbyStations.tsx   — Station list with live tide badges
      TideEventList.tsx    — Today's tide events with current highlight
      CalendarOptions.tsx  — ICS event type checkboxes
      AlertRadiusSlider.tsx
      DownloadButton.tsx   — Shows event counts, links to ICS
      ComingUpFeed.tsx     — Upcoming alerts and opportunities
      LocationSearch.tsx   — Debounced geocode autocomplete
      NavBar.tsx / TopBar.tsx
    api.ts           — All fetch functions + TypeScript types
    station-store.ts — localStorage for last-selected station
    tokens.ts        — Design system colors

scripts/
  delete_tide_events.gs  — Google Apps Script: bulk-remove tide events

tests/               — 45 Python tests, 21 TypeScript tests
cache/               — SQLite DB (auto-created, gitignored)
TODO.md              — Remaining work: map page, missing tests, viz layer
```

---

## Notes and limitations

- **US only** — NOAA CO-OPS covers the contiguous US, Alaska, Hawaii, and US territories. No international stations.
- **Nearest station substitution** — if you search "Edmonds WA" and there's no station there, the app uses the nearest one (Seattle, 14 miles). The CLI prints a note; the web app shows a banner.
- **Tidal heights are relative to MLLW** (Mean Lower Low Water) — the average of all lower low water heights. Negative heights are normal and mean the tide is below the average low.
- **Times are in the station's local time** — standard or daylight, whichever applies on that date.
- **Harmonic stations** — slack water and tidepooling features require a harmonic station. These are the primary stations with full tidal constituent analysis. Subordinate stations (marked "no" in the Harmonic column) have predicted tides but not the 6-minute curves needed for those features.
- **The `tideline` command** — available after `pip install -e .`. Without it, use `python -m app.cli` as a drop-in for every example above.
