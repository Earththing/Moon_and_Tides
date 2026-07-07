# Tideline — Remaining Work

Pick up from here. All phases 1–5 are complete and tested (50 Python tests, 41 TS tests),
including the interactive Map page. Below is what's still open.

---

## High priority

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

### Flood risk rarely fires from predictions alone
`check_flood_risk` now works (see 2026-07-07 fixes below), but NOAA's derived
thresholds sit ~1.75 ft above MHHW, so purely astronomical predictions rarely
cross them (Seattle 2026: 0 days; Charleston 2026: 0 days). Real nuisance
flooding needs storm surge on top of the prediction. Possible enhancement:
also flag highs within some margin (e.g. 0.5 ft) of the minor threshold as
"near flood stage".

---

## Completed (for reference)
- 2026-07-07: Tidepooling no longer harmonic-gated (needs only hilo +
  sunrise/sunset, which subordinate stations have); slack water remains
  harmonic-only
- 2026-07-07: Subordinate prediction stations — station list switched to
  mdapi type=tidepredictions (3,498 stations); Edmonds etc. resolve to their
  own NOAA-corrected predictions; day curve synthesized from hilo (cosine)
  where NOAA has no 6-min product; map/status parallelized
- 2026-07-07: Map page (`/map`) — CoastalMap (React-Leaflet), color-by modes,
  filter pills, radius ring, station panel with badges + sparkline, radius ICS
  download; batch endpoint `GET /api/v1/map/status`
- 2026-07-07: Fixed tidepooling timezone bug (compared UTC ephem sunrise/sunset
  to local tide times — returned [] on the West Coast); now uses localized
  `solar_cache.get_solar_day`
- 2026-07-07: Fixed flood levels — NOAA response parsed wrong (expected nested
  'self' dict; it's flat nos_*/nws_* fields) and values are STND-referenced,
  now converted to MLLW via the station datums endpoint
- Phase 1: tide_data, station_finder, ics_builder, cli (15 tests)
- Phase 2: FastAPI all endpoints including solar-day and ics-preview (10 tests)
- Phase 3: MCP server 13 tools — slack_water, tidepooling, perigean now wired to real Phase 4 code (7 tests)
- Phase 4: alert_engine, special_events (12 tests)
- Phase 5 UI: Dashboard, chart (day/week/month/year), day/night shading, date nav,
  alerts page, help page, location search, download button with event counts (21 tests)
- ICS builder: all 9 event types implemented (hilo, king tide, extreme low, perigean,
  flood risk, tidepooling, slack water, radius alerts) with count summary
- Google Apps Script cleanup tool updated for all event types
