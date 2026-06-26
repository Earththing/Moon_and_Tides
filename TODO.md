# Tideline — Remaining Work

Pick up from here. All phases 1–4 are complete and tested (44 Python tests, 21 TS tests).
Phase 5 frontend is largely complete. Below is what's still open.

---

## High priority

### Map page (`/map` route)
Currently a stub: "Map view coming in a future update."

The spec requires a full interactive map:
- React-Leaflet with CartoDB Positron tiles
- Station markers as circles: size = tidal range, color = current tide state
  - `#1b7faa` = at/near high, `#5bbfde` = rising, `#2a9e6a` = at/near low,
    `#88cc88` = falling, `#e8a030` = king tide alert
- Dashed radius ring centered on user location (`#5bbfde`)
- Hover tooltip: station name, current height, direction arrow, next tide
- Click → selects station, highlights in right panel
- Top-left "Color by" radio: current state / daily range / extremity %
- Top-right color legend
- Bottom filter pills: All / Harmonic only / Has flood data / King tide today
- Right station-list panel with live tide badges and mini sparkline for selected station
- Footer download button: "Download .ics (N mi radius)"

File to create: `frontend/src/pages/MapPage.tsx` (currently a stub)
Also needs: `frontend/src/components/CoastalMap.tsx`

---

### Missing frontend tests
These tests are listed in the spec but not yet written:

```typescript
test('Dashboard: three-column grid when feed has content')
test('Dashboard: two-column grid when feed is empty')
test('NearbyStations: alert badge shown for station with king tide')
```

Files: `frontend/src/__tests__/Dashboard.test.tsx` (new)

---

## Medium priority

### Cache trimming (future, not urgent)
The SQLite cache in `cache/tides.db` grows indefinitely by design. Past-year NOAA
predictions are kept forever (they're immutable). If the DB ever becomes large,
add a cleanup tool to remove predictions for years more than N years in the past,
or stations the user has never accessed. Solar data (~200 bytes/day) is tiny.

Relevant tables: `predictions`, `solar_days`. Tables that should never be trimmed:
`stations`, `tidal_ranges`, `flood_levels`, `perigean_events`.

---

### Slack water in ICS is slow
`options.slack` in `build_tidal_ics` works but iterates every day in a year and calls
`get_water_level_curve()` for each — that's 365 API calls on cache miss.
The CLI currently defaults `slack: False` to avoid this.

Fix options:
- Pre-fetch the full year of 6-min curve data in one NOAA call and cache it,
  then scan for inflection points in memory. The `get_water_level_curve` function
  already caches per year — just needs the full year fetched once.
- Or: add a `--slack` flag to CLI and document the slowness.

### Week view hourly curve
The spec says week view should use "hourly curve (168 pts)" but currently shows
hilo data connected as a line. NOAA supports 6-min predictions for full years,
so hourly could be derived by downsampling the cached curve. Alternatively,
keep the current hilo approach (it's arguably cleaner).

---

## Low priority / optional

### Visualization layer (`viz/` directory)
Requires `pip install tideline[viz]` (matplotlib, cartopy, numpy — not installed by default).

- `viz/tide_curve.py` — matplotlib area chart, same data as the web chart
- `viz/coast_map.py` — cartopy coast map with station dots, batch mode for animation frames
- `viz/make_video.py` — ffmpeg wrapper to combine frames into MP4

These are standalone CLI tools, not required for the web app or MCP server.

### MCP `check_flood_risk` improvement
Currently returns raw flood risk records. Should include `moderate_ft` and `major_ft`
thresholds in the output (only `minor_ft` is returned now).

### ICS calendar name
Currently named `"Tides — {station_id} {year}"`. Could use the station name instead:
`"Tides — Seattle 2026"`. The station name is already available in `build_tidal_ics`.

---

## Completed (for reference)
- Phase 1: tide_data, station_finder, ics_builder, cli (15 tests)
- Phase 2: FastAPI all endpoints including solar-day and ics-preview (10 tests)
- Phase 3: MCP server 13 tools — slack_water, tidepooling, perigean now wired to real Phase 4 code (7 tests)
- Phase 4: alert_engine, special_events (12 tests)
- Phase 5 UI: Dashboard, chart (day/week/month/year), day/night shading, date nav,
  alerts page, help page, location search, download button with event counts (21 tests)
- ICS builder: all 9 event types implemented (hilo, king tide, extreme low, perigean,
  flood risk, tidepooling, slack water, radius alerts) with count summary
- Google Apps Script cleanup tool updated for all event types
