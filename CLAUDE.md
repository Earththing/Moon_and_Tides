# Moon & Tides: Tideline — Claude Code Spec

> Part of the Moon & Tides suite — companion to Sun & Seasons Calendar. Same architecture: FastAPI · CLI · MCP server · visualization.
> Primary data: NOAA CO-OPS API (free, no key required, US coastal).
> Language split: Python for all backend/data/MCP/ICS. TypeScript/React for UI only.

---

## Work rules

- Implement phases in order. Do not start Phase N+1 until Phase N tests are green.
- After each module: run `pytest tests/ -m "not live and not slow" -v`. Fix all failures before continuing.
- Never delete or xfail a test to make the suite pass. If a test is wrong, fix the test with a comment explaining why.
- Commit after each module passes: `git add -A && git commit -m "phase N: module_name passing"`
- Cache all NOAA API responses in SQLite. Never make the same API call twice in tests.
- Mark any test that hits the real NOAA API with `@pytest.mark.live`.
- Match function signatures exactly as specified — MCP tools depend on them.
- Report `PHASE N COMPLETE: X tests passing` before starting the next phase.

---

## pyproject.toml

```toml
[project]
name = "tideline"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
tideline = "app.cli:main"
tideline-mcp = "mcp_server:main"

[project.optional-dependencies]
viz = ["matplotlib>=3.8", "cartopy>=0.22", "numpy>=1.26"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27",
       "ruff>=0.4", "icalendar>=5.0"]

[tool.pytest.ini_options]
markers = [
    "live: hits real NOAA API",
    "slow: long-running batch operations",
    "viz: requires matplotlib/cartopy extras",
]
```

## requirements.txt

```
fastapi>=0.111
uvicorn[standard]>=0.29
httpx>=0.27
geopy>=2.4
timezonefinder>=6.5
icalendar>=5.0
mcp>=1.0
pydantic>=2.7
ephem>=4.1
```

---

## Project structure

```
moon_and_tides/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── tide_data.py
│   ├── station_finder.py
│   ├── ics_builder.py
│   ├── alert_engine.py
│   ├── special_events.py
│   ├── tidal_types.py
│   ├── geocode.py
│   └── cli.py
├── viz/
│   ├── tide_curve.py
│   ├── coast_map.py
│   └── make_video.py
├── frontend/          ← Phase 5 only
├── static/
├── templates/
├── tests/
├── cache/             ← gitignored
├── mcp_server.py
├── pyproject.toml
├── requirements.txt
└── .gitignore
```

---

## Phase 1 — Core data + ICS

### `app/tide_data.py`

```python
def get_hilo_predictions(
    station_id: str,
    begin_date: str,       # "YYYYMMDD"
    end_date: str,
    datum: str = "MLLW",
    units: str = "english",
    time_zone: str = "lst_ldt"
) -> list[dict]:
    # Returns: [{date, time, height_ft, type}]  type: "H"|"L"
    # Cache by (station_id, year) in SQLite at cache/tides.db
    # Cache lifetime: 30 days
    # On cache miss: fetch NOAA, store, return
    # On fetch failure: return cached if available, else raise
    # NOAA endpoint: api.tidesandcurrents.noaa.gov/api/prod/datagetter
    # Params: product=predictions, interval=hilo, format=json
    # Include: application=moon_and_tides/0.1 in all NOAA requests

def get_water_level_curve(
    station_id: str,
    date: str,             # "YYYYMMDD"
    datum: str = "MLLW",
    units: str = "english"
) -> list[dict]:
    # Returns: [{time, height_ft}] at 6-minute intervals
    # Used for visualization only, not ICS

def get_station_tidal_range(station_id: str) -> dict:
    # Returns: {mean_range_ft, mean_high_ft, mean_low_ft}
    # Compute from 1 year of hilo predictions
```

SQLite schema:
```sql
CREATE TABLE IF NOT EXISTS predictions (
    station_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    product TEXT NOT NULL,  -- "hilo" or "curve"
    datum TEXT NOT NULL,
    units TEXT NOT NULL,
    json_data TEXT NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    PRIMARY KEY (station_id, year, product, datum, units)
);

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
);

CREATE TABLE IF NOT EXISTS tidal_ranges (
    station_id TEXT PRIMARY KEY,
    mean_range_ft REAL,
    mean_high_ft REAL,
    mean_low_ft REAL,
    computed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS flood_levels (
    station_id TEXT PRIMARY KEY,
    minor_ft REAL,
    moderate_ft REAL,
    major_ft REAL,
    fetched_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS perigean_events (
    year INTEGER PRIMARY KEY,
    json_data TEXT,
    computed_at TIMESTAMP
);
```

### `app/station_finder.py`

```python
def get_all_stations() -> list[dict]:
    # Fetch from NOAA MDAPI, cache in SQLite for 7 days
    # Endpoint: mdapi/prod/webapi/stations.json?type=waterlevels
    # Returns: [{id, name, lat, lon, state, tidal, harmonic}]

def find_nearest_stations(
    lat: float, lon: float,
    max_results: int = 5,
    max_radius_miles: float = 100.0,
    require_harmonic: bool = False
) -> list[dict]:
    # Returns nearest stations sorted by distance
    # Each: {id, name, lat, lon, distance_miles, harmonic}

def find_stations_in_radius(
    lat: float, lon: float,
    radius_miles: float
) -> list[dict]:
    # All stations within radius, sorted by distance

def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    # Standard haversine

def get_tidal_type(station_id: str) -> dict:
    # Returns: {type: "diurnal"|"semidiurnal"|"mixed", description}
    # Derived from harmonic constituents if available
    # Fallback: classify from ratio of daily tide counts over 30 days
    #   diurnal: avg < 1.5 tides/day
    #   semidiurnal: avg > 1.8 tides/day with similar heights
    #   mixed: two highs/day with noticeably different heights
```

### `app/ics_builder.py`

RFC 5545 compliant. Requirements:
- CRLF line endings
- 75-octet line folding
- VTIMEZONE component
- Stable UIDs: `tide-{station_id}-{date}-{HHMM}-{type}@tideline`
- Use `icalendar` library

Event types:

| Type | Title | DTSTART | Duration |
|---|---|---|---|
| High tide | `🌊 High Tide — {h} ft` | tide time | 15 min |
| Low tide | `🏖 Low Tide — {h} ft` | tide time | 15 min |
| Extreme high | `⚠️ King Tide — {h} ft` | all-day DATE | all-day |
| Extreme low | `⚠️ Extreme Low — {h} ft` | all-day DATE | all-day |
| Radius alert | `🌊 King Tide Nearby: {station} ({dist} mi) — {h} ft` | all-day | all-day |
| Slack water | `⚓ Slack Water` | slack time | 10 min |
| Tidepooling | `🦀 Tidepooling Window — Low: {h} ft at {time}` | all-day | all-day |
| Flood risk | `🚨 Flood Risk: {level} — {h} ft` | all-day | all-day |
| Perigean | `🌕 Perigean Spring Tide` | all-day | all-day |

Description field for high/low events:
```
Height: {h} ft ({h_m} m)
Datum: MLLW
Station: {name} ({id})
Next {low|high} tide: {time} — {h} ft
```

```python
def build_tidal_ics(
    station_id: str,
    year: int,
    options: dict = None  # {hilo, alerts, slack, tidepooling, flood, perigean, radius}
) -> bytes:
    # Returns raw ICS bytes

def build_alerts_only_ics(station_id: str, year: int, ...) -> bytes:
    # Returns ICS with only all-day alert events
```

### `app/cli.py`

```
tideline tides "San Francisco, CA"
tideline tides "San Francisco, CA" --year 2026
tideline tides "San Francisco, CA" --date 2026-06-21
tideline tides --station 9414290 --year 2026
tideline tides --lat 37.8 --lon -122.47

tideline stations "Bodega Bay, CA" --radius 50
tideline stations "Bodega Bay, CA" --count 5

tideline ics "San Francisco, CA" --year 2026
tideline ics "San Francisco, CA" --year 2026 --out sf_tides_2026.ics
tideline ics "San Francisco, CA" --year 2026 --alerts-only
tideline ics "San Francisco, CA" --year 2026 --radius 75

tideline extremes "San Francisco, CA" --year 2026
tideline extremes "San Francisco, CA" --radius 100 --year 2026

tideline preview "San Francisco, CA"
```

### Phase 1 tests (`tests/test_tide_data.py`, `test_station_finder.py`, `test_ics_builder.py`)

```python
# tide_data
def test_hilo_returns_valid_structure():
    data = get_hilo_predictions("9414290", "20260101", "20260131")
    assert len(data) > 50
    assert all("height_ft" in d and "type" in d for d in data)
    assert all(d["type"] in ("H", "L") for d in data)

def test_hilo_alternates():
    data = get_hilo_predictions("9414290", "20260101", "20260131")
    types = [d["type"] for d in data]
    for i in range(len(types) - 1):
        assert types[i] != types[i+1]

def test_caching_returns_same_data():
    a = get_hilo_predictions("9414290", "20260101", "20260131")
    b = get_hilo_predictions("9414290", "20260101", "20260131")
    assert a == b

def test_height_values_plausible():
    data = get_hilo_predictions("9414290", "20260101", "20261231")
    highs = [d["height_ft"] for d in data if d["type"] == "H"]
    lows  = [d["height_ft"] for d in data if d["type"] == "L"]
    assert min(lows) > -2.0 and max(highs) < 8.0

# station_finder
def test_nearest_to_sf():
    stations = find_nearest_stations(37.7749, -122.4194, max_results=1)
    assert stations[0]["id"] == "9414290"

def test_radius_bounds():
    stations = find_stations_in_radius(37.7749, -122.4194, 50)
    assert len(stations) >= 3
    assert all(s["distance_miles"] <= 50 for s in stations)

# ics_builder
def test_ics_parses():
    from icalendar import Calendar
    ics = build_tidal_ics("9414290", 2026)
    cal = Calendar.from_ical(ics)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) > 600

def test_ics_uids_stable():
    from icalendar import Calendar
    def uids(ics): return {c["UID"] for c in Calendar.from_ical(ics).walk() if c.name == "VEVENT"}
    assert uids(build_tidal_ics("9414290", 2026)) == uids(build_tidal_ics("9414290", 2026))

def test_ics_uids_unique():
    from icalendar import Calendar
    ics = build_tidal_ics("9414290", 2026)
    uids = [c["UID"] for c in Calendar.from_ical(ics).walk() if c.name == "VEVENT"]
    assert len(uids) == len(set(uids))

def test_ics_crlf():
    ics = build_tidal_ics("9414290", 2026)
    assert b"\r\n" in ics
    assert b"\n\n" not in ics
```

**Phase 1 acceptance:** `tideline ics "San Francisco, CA" --year 2026` produces a valid importable ICS file.

---

## Phase 2 — Web app (FastAPI)

### `app/main.py` routes

```
POST /geocode
  body: {address: str}
  returns: [{lat, lon, display_name}]

GET /api/v1/stations/nearest
  ?lat=&lon=&count=5&require_harmonic=false
  returns: [{id, name, lat, lon, distance_miles, harmonic, tidal_type}]

GET /api/v1/stations/radius
  ?lat=&lon=&radius_miles=75
  returns: [{id, name, lat, lon, distance_miles, harmonic}]

GET /api/v1/station/{station_id}
  returns: {id, name, lat, lon, state, harmonic, tidal_type,
            mean_range_ft, mean_high_ft, mean_low_ft,
            has_flood_thresholds, flood_minor_ft, flood_moderate_ft}

GET /api/v1/tides/day
  ?station_id=&date=YYYY-MM-DD&datum=MLLW&units=english
  returns: {hilo: [{time, height_ft, type}], curve: [{time, height_ft}]}

GET /api/v1/tides/range
  ?station_id=&begin=YYYY-MM-DD&end=YYYY-MM-DD
  returns: {hilo: [...]}

GET /api/v1/tides/year-summary
  ?station_id=&year=
  returns: {monthly_mean_high: [...12], monthly_mean_low: [...12],
            extreme_highs: [...], extreme_lows: [...]}

GET /api/v1/special-events
  ?station_id=&year=&lat=&lon=&radius_miles=
  returns: {tidepooling_windows, slack_water, perigean_spring_tides,
            radius_alerts, flood_risk}

GET /calendar/{year}/{lat},{lon}.ics
  ?options=hilo,alerts,slack,tidepooling,perigean,radius&radius_miles=75
  streams: ICS file download

GET /calendar/{year}/{lat},{lon}-alerts.ics
  streams: alerts-only ICS
```

**Phase 2 acceptance:** Web app at localhost:8000, all API endpoints return valid JSON, ICS download works.

---

## Phase 3 — MCP server

### `mcp_server.py` tools

| Tool | Parameters | Returns |
|---|---|---|
| `geocode` | `address: str` | `[{lat, lon, display_name}]` |
| `find_stations` | `lat, lon, max_results?, max_radius_miles?` | station list |
| `get_tides_day` | `station_id, date` | `[{time, height_ft, type}]` |
| `get_tides_range` | `station_id, begin_date, end_date` | hilo list |
| `get_station_info` | `station_id` | full station metadata |
| `get_tidal_type` | `station_id` | `{type, description}` |
| `get_extreme_tides` | `station_id, begin_date, end_date, percentile?` | extreme events |
| `find_extreme_in_radius` | `lat, lon, radius_miles, begin_date, end_date` | cross-station extremes |
| `check_flood_risk` | `station_id, begin_date, end_date` | flood risk events |
| `get_slack_water` | `station_id, date` | `[{time, direction}]` |
| `get_tidepooling_windows` | `station_id, begin_date, end_date, lat, lon` | windows list |
| `get_perigean_spring_tides` | `year` | `[{date, description}]` |
| `generate_ics_url` | `lat, lon, year, options?` | URL string |

Claude Desktop config:
```json
{
  "mcpServers": {
    "tideline": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}
```

**Phase 3 acceptance:** Claude can answer "When is high tide in Seattle tomorrow?" and "Find the lowest tide within 50 miles of San Francisco in July 2026" using only MCP tools.

---

## Phase 4 — Alert engine + special events

### `app/alert_engine.py`

```python
def compute_extreme_thresholds(
    station_id: str,
    percentile_high: float = 0.90,
    percentile_low: float = 0.10
) -> dict:
    # {high_threshold_ft, low_threshold_ft}

def find_extreme_tides(
    station_id: str, begin_date: str, end_date: str,
    high_threshold_ft: float = None, low_threshold_ft: float = None
) -> list[dict]:

def find_extreme_in_radius(
    lat: float, lon: float, radius_miles: float,
    begin_date: str, end_date: str,
    percentile_threshold: float = 0.90
) -> list[dict]:
    # [{date, time, height_ft, type, station_id, station_name, distance_miles, percentile}]

def check_flood_risk(station_id: str, begin_date: str, end_date: str) -> list[dict]:
    # Uses NOAA flood thresholds from mdapi/prod/webapi/stations/{id}/floodlevels.json
    # [{date, predicted_high_ft, minor_ft, flood_level: "minor"|"moderate"|"major"|None}]
```

### `app/special_events.py`

```python
def get_slack_water(station_id: str, date: str) -> list[dict]:
    # Inflection points of 6-minute water level curve
    # [{time, between: "high_to_low"|"low_to_high"}]
    # Requires harmonic station

def get_tidepooling_windows(
    station_id: str, begin_date: str, end_date: str,
    lat: float, lon: float
) -> list[dict]:
    # Days where lowest tide occurs during daylight hours
    # Uses get_solar_day() for sunrise/sunset
    # Score: lower tide + closer to solar noon = better
    # [{date, low_tide_time, low_height_ft, sunrise, sunset, score}]

def get_perigean_spring_tides(year: int) -> list[dict]:
    # Uses ephem library for lunar perigee + new/full moon dates
    # Flags dates where perigee within 24h of syzygy
    # [{date, moon_phase, perigee_distance_km, description}]

def get_tidal_bore_times(location_name: str, date: str) -> dict | None:
    # Hardcoded bore locations with offset tables
    # Returns bore ETA or None if not a bore location
    BORE_OFFSETS = {
        "turnagain_arm_ak": {"ref_station": "9455090", "offset_hours": 2.5},
        # add others
    }
```

**Phase 4 acceptance:** `tideline ics "San Francisco, CA" --year 2026 --radius 75` includes all-day alert events for king tides within 75 miles.

---

## Phase 5 — React/TypeScript frontend

### Setup

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom recharts react-leaflet leaflet swr
npm install -D tailwindcss autoprefixer @types/leaflet vitest @testing-library/react
npx tailwindcss init -p
```

### `vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/geocode': 'http://localhost:8000',
      '/calendar': 'http://localhost:8000',
    }
  }
})
```

### Design system — Coastal Warm

```typescript
// src/tokens.ts
export const tokens = {
  ocean:         '#1b3a5c',  // nav bg, station panel bg, headings
  oceanLight:    '#1b7faa',  // high tide dots, primary actions, chart line, download btn
  sky:           '#5bbfde',  // "now" cursor, selected station border, active badges
  sea:           '#2a9e6a',  // low tide dots
  amberBorder:   '#e8c060',  // alert feed item border
  amberBg:       '#fffaf0',  // alert feed item background
  amberText:     '#a06000',  // alert feed item text
  goodBorder:    '#a8dfc0',  // positive event border (tidepooling)
  goodBg:        '#f4fbf7',  // positive event background
  danger:        '#a32d2d',  // flood risk
  surface:       '#f0f4f8',  // app/page background
  card:          '#ffffff',  // card and column backgrounds
  cardAlt:       '#f8fafb',  // middle column background (slightly off-white)
  border:        '#d0d8e4',  // all borders and dividers
  borderLight:   '#e8eef4',  // tide row borders
  textPrimary:   '#1b3a5c',
  textSecondary: '#7a8fa3',
  textHint:      '#a0b0bf',
}
```

Tailwind config extends these as custom colors.

---

### Layout — Hybrid (chart-hero + smart feed)

The dashboard has four zones stacked vertically:

```
┌─────────────────────────────────────────────────────┐
│ Nav bar (ocean bg, logo + links)                    │
├─────────────────────────────────────────────────────┤
│ Top bar (location name, station ID, view toggle)    │
├─────────────────────────────────────────────────────┤
│ Full-width tide curve chart                         │
├──────────────┬──────────────────────┬───────────────┤
│ Left col     │ Middle col           │ Right col     │
│ Nearby       │ Today's tides        │ Coming up     │
│ stations     │ + calendar options   │ (FEED)        │
│ + stats      │ + download btn       │               │
└──────────────┴──────────────────────┴───────────────┘
```

**Critical layout behavior — smart feed:**
- When feed has content: `grid-template-columns: 220px 1fr 200px` (three columns)
- When feed is empty: `grid-template-columns: 220px 1fr` (two columns, right col gone)
- Never render an empty right column. No "nothing to show" placeholder.
- Feed content is determined server-side: if `specialEvents` response has no items for the next 30 days, omit the right column entirely.

```typescript
// Layout logic in Dashboard.tsx
const hasFeedContent = specialEvents.upcoming.length > 0
const gridClass = hasFeedContent
  ? 'grid-cols-[220px_1fr_200px]'
  : 'grid-cols-[220px_1fr]'
```

---

### Left column — `NearbyStations`

- Station cards with: name, station ID, distance in miles, harmonic badge
- Each card shows a **live tide badge**: current height + direction arrow (↑/↓)
  - High tide state: `bg-[#eaf4fb] text-[#1b7faa]`
  - Low tide state: `bg-[#e8f6ef] text-[#2a9e6a]`
  - Alert state (king tide): `bg-[#fff3dc] text-[#a06000]` with ⚠ prefix
- Selected station: `border-[#1b7faa] bg-[#eaf4fb]`
- Clicking a station updates all data panels and the URL
- Below station list: **Station stats** section (divider + label)
  - Tidal range, tidal type, datum, timezone — simple label/value rows
- When a diurnal station is selected: show a one-paragraph explanation card
  explaining what diurnal means (blue-tinted info box)

### Middle column — `TidePanel`

Sections in order, each separated by a labeled divider:

1. **Today's tides** — tide event rows
   - Each row: time (tabular-nums, 50px fixed) · colored dot · label · height right-aligned
   - Current event highlighted: `bg-[#e5f4fb]` row, label text `text-[#1b7faa] font-semibold`
   - High dot: `bg-[#1b7faa]`, low dot: `bg-[#2a9e6a]`

2. **Calendar options** — checkboxes
   - Cannot uncheck: High & low tides
   - Disabled + tooltip when station is non-harmonic: Slack water, Tidepooling
   - Disabled + tooltip when no NOAA flood data: Flood risk
   - Disabled when radius ≤ 10 mi: Radius alerts
   - Greyed text + cursor-not-allowed on disabled items

3. **Alert radius slider** — range 10–150 mi, step 5, shows "X mi · N stations"

4. **Download button** — `bg-[#1b7faa] text-white`, flat, full width, always visible

### Right column — `ComingUpFeed` (conditional)

Feed items, each a card with colored left treatment:

| Type | Background | Border | Emoji |
|---|---|---|---|
| Alert (king tide, flood) | `#fffaf0` | `#e8c060` | ⚠️ |
| Opportunity (tidepooling) | `#f4fbf7` | `#a8dfc0` | 🦀 |
| Informational (slack, perigean) | `#ffffff` | `#e0e8f0` | ⚓ 🌕 |

Each item: bold title, 2-line description with key fact in bold.

Column header: "Coming up" — next 30 days, max 6 items, sorted by date.
If > 6 items: show 6 + "View all →" link that navigates to `/alerts`.

---

### TideCurveChart spec

```typescript
interface TideCurveChartProps {
  curveData:   { time: string; height_ft: number }[]  // 6-min intervals for day/week
  hiloData:    { time: string; height_ft: number; type: 'H' | 'L' }[]
  floodMinor?: number   // renders dashed red ReferenceLine if present
  view:        'day' | 'week' | 'month' | 'year'
  stationId:   string
}
```

- Recharts `<AreaChart>` with `<Area>` stroke `#1b7faa`, fill gradient `#1b7faa` 20% → 2%
- `<ReferenceDot>` at each hilo extremum: blue for H, green for L, with height label
- `<ReferenceLine>` at current time: `stroke="#5bbfde"` dashed, "now" label
- `<ReferenceLine>` at flood minor level: `stroke="#a32d2d"` dashed, only if `floodMinor` prop present
- View modes:
  - Day: 6-min curve (240 pts) + hilo dots
  - Week: hourly curve (168 pts) + hilo dots
  - Month: hilo dots only, no curve
  - Year: `<BarChart>` of monthly mean high/low

---

### Map screen (`/map` route)

Full-page layout: map occupies left ~65%, station list panel on right 35%.

**Map (React-Leaflet + CartoDB Positron):**
- Station markers: circles, size = tidal range, color = current tide state
  - `#1b7faa` = at/near high, `#5bbfde` = rising, `#2a9e6a` = at/near low, `#88cc88` = falling, `#e8a030` = king tide alert
- Radius overlay: dashed `#5bbfde` circle centered on user location
- Hover tooltip: station name, current height, direction, next tide
- Click: selects station, highlights it in right panel list
- Top-left control panel: "Color by" radio (current state / daily range / extremity %), radius slider
- Top-right: color legend
- Bottom filter bar: pill buttons — All stations / Harmonic only / Has flood data / King tide today

**Right station list panel:**
- Dark ocean header: "Stations in range · N mi radius"
- Station cards with live tide badge (same as dashboard left col)
- Selected station shows mini spark-line of today's tide curve
- Footer: "Download .ics (N mi radius)" button covering all stations in range

---

### React Router routes

```
/                               → Dashboard, last used location or prompt
/station/:stationId             → Dashboard, station pre-selected
/station/:stationId/year/:year  → Dashboard with year override
/map                            → Full map screen
/alerts                         → Full alerts feed (overflow from dashboard feed)
/help                           → Help + import instructions
```

URL must fully reconstruct state — `/station/9414290/year/2026` works as a shareable link.

---

### Component implementation order

1. `App` + router skeleton + `tokens.ts`
2. `NavBar`
3. `TopBar` — location display + `ViewToggle`
4. `TideCurveChart` — Recharts, all view modes, flood line, now cursor
5. `NearbyStations` — station cards with live tide badges, diurnal explanation card
6. `TideEventList` — tide rows with current highlight
7. `CalendarOptions` — checkboxes, disabled states, tooltips
8. `AlertRadiusSlider` — live station count
9. `DownloadButton` — ICS URL construction
10. `ComingUpFeed` — feed items, color types, conditional render
11. `Dashboard` — assembles all above, smart grid (2 or 3 col)
12. `LocationSearch` — geocode input, debounced 300ms, autocomplete
13. `CoastalMap` — Leaflet, station dots, radius ring, filters, tooltip, station panel
14. `AlertsFeed` — full-page `/alerts` view

### CalendarOptions disabled states

```typescript
const isHarmonic = selectedStation?.harmonic ?? false
const hasFloodData = selectedStation?.has_flood_thresholds ?? false
const radiusActive = radiusMiles > 10

// Disabled (greyed, cursor-not-allowed, tooltip on hover):
// slack water:    !isHarmonic  → "Requires a harmonic station"
// tidepooling:    !isHarmonic  → "Requires a harmonic station"
// flood risk:     !hasFloodData → "No NOAA flood thresholds for this station"
// radius alerts:  !radiusActive → "Set alert radius above 10 miles"

// Cannot be unchecked — always true:
// high & low tides
```

### Frontend tests (Vitest)

```typescript
test('TideCurveChart: day view renders without error with 240 data points')
test('TideCurveChart: flood ReferenceLine absent when floodMinor prop not provided')
test('TideCurveChart: flood ReferenceLine present when floodMinor prop provided')
test('TideCurveChart: now ReferenceLine is within chart x-axis range')
test('Dashboard: three-column grid when feed has content')
test('Dashboard: two-column grid when feed is empty')
test('NearbyStations: alert badge shown for station with king tide')
test('NearbyStations: diurnal explanation card shown for diurnal station')
test('CalendarOptions: slack water disabled when station is non-harmonic')
test('CalendarOptions: flood risk disabled when station has no flood data')
test('CalendarOptions: radius alerts disabled when radius at minimum')
test('CalendarOptions: high & low tides checkbox cannot be unchecked')
test('AlertRadiusSlider: station count label updates when value changes')
test('LocationSearch: geocode not called until 300ms after last keystroke')
test('LocationSearch: selecting candidate calls onSelect with lat/lon')
test('DownloadButton: constructs correct ICS URL from station, year, options')
test('ComingUpFeed: alert items rendered with amber styling')
test('ComingUpFeed: tidepooling items rendered with green styling')
```

**Phase 5 acceptance:** All vitest tests pass. App renders at localhost:5173 with FastAPI on 8000. Dashboard collapses to two columns on a station with no upcoming events. Map screen shows station dots colored by tide state.

---

## Visualization layer (Phase 5, Python — requires `[viz]` extras)

### `viz/tide_curve.py`

```bash
python viz/tide_curve.py --station 9414290 --date 2026-06-21
python viz/tide_curve.py --station 9414290 --week 2026-W25
python viz/tide_curve.py --station 9414290 --month 2026-06
```

- Matplotlib AreaChart equivalent
- Blue filled area, high dots ocean blue, low dots sea green
- NOAA flood threshold as dashed red line if available
- Output: PNG

### `viz/coast_map.py`

```bash
python viz/coast_map.py --date 2026-06-21 --region west_coast
python viz/coast_map.py --year 2026 --no-show   # batch 365 frames
```

Regions: `west_coast`, `east_coast`, `gulf`, `alaska`, `hawaii`, `all`
Station dot color: relative tide height (blue=low, green=mean, amber=high, red=flood)
Station dot size: tidal range

### `viz/make_video.py`

```bash
python viz/make_video.py --frames viz/frames/ --out viz/tides_2026.mp4 --fps 24
```

---

## Claude Code loop commands

```bash
# Phase 1
claude --dangerously-skip-permissions \
  "Implement Phase 1 of CLAUDE.md. \
   Run pytest tests/ -m 'not live and not slow' after each module. \
   Fix failures before next module. Commit when module passes. \
   Stop and report PHASE 1 COMPLETE when all Phase 1 tests pass."

# Phase 2
claude --dangerously-skip-permissions \
  "Phase 1 is complete. Implement Phase 2 of CLAUDE.md. \
   Same rules: test after each route group, fix failures, commit. \
   Report PHASE 2 COMPLETE when all tests pass."

# Continue pattern for phases 3, 4

# Phase 5 (run with FastAPI already started on port 8000)
claude --dangerously-skip-permissions \
  "Implement Phase 5 frontend per CLAUDE.md. \
   Scaffold with vite react-ts, install deps, implement components \
   in the listed order, run vitest after each. \
   Report FRONTEND COMPLETE when vitest passes 100%."

# Resume after interruption
claude --dangerously-skip-permissions \
  "Run pytest tests/ -m 'not live and not slow'. \
   Tell me which phases are passing. \
   Continue implementing the next failing phase per CLAUDE.md."
```
