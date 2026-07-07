import { useEffect, useMemo, useState } from 'react'
import NavBar from '../components/NavBar'
import CoastalMap, { type MapStation } from '../components/CoastalMap'
import {
  fetchStationsRadius, fetchMapStatus, fetchTidesDay, icsUrl,
  type Station, type MapStationStatus, type CurvePoint,
} from '../api'
import { loadLocation } from '../station-store'
import { computeTideStatus, type ColorMode, MAP_COLORS } from '../tide-status'

const DEFAULT_LAT = 47.6062
const DEFAULT_LON = -122.3321
const MAX_STATIONS = 60

type FilterMode = 'all' | 'harmonic' | 'flood' | 'king'

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function nowMinutes() {
  const d = new Date()
  return d.getHours() * 60 + d.getMinutes()
}

/** Tiny SVG sparkline of today's tide curve for the selected station card. */
function Sparkline({ curve }: { curve: CurvePoint[] }) {
  if (curve.length < 2) return null
  const w = 160, h = 36
  const hs = curve.map(p => p.height_ft)
  const min = Math.min(...hs), max = Math.max(...hs)
  const span = max - min || 1
  const pts = curve
    .map((p, i) => `${((i / (curve.length - 1)) * w).toFixed(1)},${(h - 3 - ((p.height_ft - min) / span) * (h - 6)).toFixed(1)}`)
    .join(' ')
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="mt-1">
      <polyline points={pts} fill="none" stroke="#1b7faa" strokeWidth="1.5" />
    </svg>
  )
}

function TideBadge({ station }: { station: MapStation }) {
  const st = station.status
  if (!st || st.heightFt == null) return null
  const dir = st.phase === 'rising' || st.phase === 'high' ? '↑' : '↓'
  if (st.kingTide) {
    return (
      <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-amberBg text-amberText border border-amberBorder whitespace-nowrap">
        ⚠ {dir} {st.heightFt.toFixed(1)} ft
      </span>
    )
  }
  const cls = st.phase === 'high' || st.phase === 'rising'
    ? 'bg-[#eaf4fb] text-oceanLight'
    : 'bg-[#e8f6ef] text-sea'
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium whitespace-nowrap ${cls}`}>
      {dir} {st.heightFt.toFixed(1)} ft
    </span>
  )
}

const LEGEND: { mode: ColorMode; items: [string, string][] }[] = [
  {
    mode: 'state',
    items: [
      [MAP_COLORS.high, 'At/near high'], [MAP_COLORS.rising, 'Rising'],
      [MAP_COLORS.low, 'At/near low'], [MAP_COLORS.falling, 'Falling'],
      [MAP_COLORS.king, 'King tide today'],
    ],
  },
  {
    mode: 'range',
    items: [['#5bbfde', 'Small daily range'], ['#3b7d9d', 'Medium'], ['#1b3a5c', 'Large (15+ ft)']],
  },
  {
    mode: 'extremity',
    items: [
      [MAP_COLORS.low, 'Well below king level'], [MAP_COLORS.rising, 'Approaching'],
      [MAP_COLORS.king, 'King tide'], ['#a32d2d', 'Extreme king tide'],
    ],
  },
]

export default function MapPage() {
  const saved = useMemo(loadLocation, [])
  const lat = saved?.lat ?? DEFAULT_LAT
  const lon = saved?.lon ?? DEFAULT_LON

  const [radiusMiles, setRadiusMiles] = useState(50)
  const [colorMode, setColorMode] = useState<ColorMode>('state')
  const [filter, setFilter] = useState<FilterMode>('all')
  const [stations, setStations] = useState<Station[]>([])
  const [statusMap, setStatusMap] = useState<Record<string, MapStationStatus>>({})
  const [extremesLoaded, setExtremesLoaded] = useState(false)
  const [floodLoaded, setFloodLoaded] = useState(false)
  const [loadingExtra, setLoadingExtra] = useState(false)
  const [selectedId, setSelectedId] = useState('')
  const [sparkCurve, setSparkCurve] = useState<CurvePoint[]>([])

  // Stations in radius
  useEffect(() => {
    fetchStationsRadius(lat, lon, radiusMiles)
      .then(list => setStations(list.slice(0, MAX_STATIONS)))
      .catch(console.error)
  }, [lat, lon, radiusMiles])

  // Base status batch (today's hilo per station)
  useEffect(() => {
    if (stations.length === 0) { setStatusMap({}); return }
    setExtremesLoaded(false)
    setFloodLoaded(false)
    fetchMapStatus(stations.map(s => s.id), todayStr())
      .then(setStatusMap)
      .catch(console.error)
  }, [stations])

  // Extremes / flood data are heavier — load lazily when a mode/filter needs them
  const needExtremes = colorMode === 'extremity' || filter === 'king'
  const needFlood = filter === 'flood'
  useEffect(() => {
    if (stations.length === 0) return
    if ((!needExtremes || extremesLoaded) && (!needFlood || floodLoaded)) return
    setLoadingExtra(true)
    fetchMapStatus(stations.map(s => s.id), todayStr(), { extremes: needExtremes, flood: needFlood })
      .then(data => {
        setStatusMap(prev => {
          const merged = { ...prev }
          for (const [id, entry] of Object.entries(data)) merged[id] = { ...merged[id], ...entry }
          return merged
        })
        if (needExtremes) setExtremesLoaded(true)
        if (needFlood) setFloodLoaded(true)
      })
      .catch(console.error)
      .finally(() => setLoadingExtra(false))
  }, [stations, needExtremes, needFlood, extremesLoaded, floodLoaded])

  // Sparkline for the selected station
  useEffect(() => {
    if (!selectedId) { setSparkCurve([]); return }
    fetchTidesDay(selectedId, todayStr())
      .then(({ curve }) => setSparkCurve(curve))
      .catch(() => setSparkCurve([]))
  }, [selectedId])

  const now = nowMinutes()
  const mapStations: MapStation[] = useMemo(
    () => stations.map(s => {
      const entry = statusMap[s.id]
      return {
        ...s,
        status: entry ? computeTideStatus(entry.hilo, now, entry.high_threshold_ft) : null,
        highThresholdFt: entry?.high_threshold_ft,
      }
    }),
    [stations, statusMap, now],
  )

  const visible = mapStations.filter(s => {
    if (filter === 'harmonic') return !!s.harmonic
    if (filter === 'flood') return statusMap[s.id]?.has_flood === true
    if (filter === 'king') return s.status?.kingTide === true
    return true
  })

  const legend = LEGEND.find(l => l.mode === colorMode)!
  const year = new Date().getFullYear()

  const pill = (mode: FilterMode, label: string) => (
    <button
      key={mode}
      onClick={() => setFilter(mode)}
      className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
        filter === mode
          ? 'bg-oceanLight text-white border-oceanLight'
          : 'bg-card text-textPrimary border-border hover:bg-surface'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="h-screen bg-surface flex flex-col">
      <NavBar />
      <div className="flex-1 flex min-h-0">
        {/* Map — left ~65% */}
        <div className="relative flex-[13] min-w-0">
          <CoastalMap
            center={[lat, lon]}
            stations={visible}
            selectedId={selectedId}
            onSelect={setSelectedId}
            radiusMiles={radiusMiles}
            colorMode={colorMode}
          />

          {/* Top-left: color-by + radius controls */}
          <div className="absolute top-3 left-3 z-[1000] bg-card border border-border rounded shadow-md p-3 w-52 space-y-2">
            <div className="text-xs font-semibold text-textSecondary uppercase tracking-wide">Color by</div>
            {([['state', 'Current state'], ['range', 'Daily range'], ['extremity', 'Extremity %']] as [ColorMode, string][]).map(
              ([mode, label]) => (
                <label key={mode} className="flex items-center gap-2 text-sm text-textPrimary cursor-pointer">
                  <input
                    type="radio"
                    name="colorby"
                    checked={colorMode === mode}
                    onChange={() => setColorMode(mode)}
                    className="accent-[#1b7faa]"
                  />
                  {label}
                </label>
              ),
            )}
            <div className="pt-1 border-t border-borderLight">
              <div className="flex justify-between text-xs text-textSecondary mb-1">
                <span>Radius</span>
                <span className="font-medium text-textPrimary">{radiusMiles} mi</span>
              </div>
              <input
                type="range"
                min={10}
                max={150}
                step={5}
                value={radiusMiles}
                onChange={e => setRadiusMiles(Number(e.target.value))}
                className="w-full accent-[#1b7faa]"
                aria-label="Alert radius"
              />
            </div>
          </div>

          {/* Top-right: legend */}
          <div className="absolute top-3 right-3 z-[1000] bg-card border border-border rounded shadow-md p-3 space-y-1">
            {legend.items.map(([color, label]) => (
              <div key={label} className="flex items-center gap-2 text-xs text-textPrimary">
                <span className="w-3 h-3 rounded-full inline-block border border-white shadow-sm" style={{ background: color }} />
                {label}
              </div>
            ))}
          </div>

          {/* Bottom: filter pills */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[1000] flex gap-2 bg-card/90 backdrop-blur border border-border rounded-full px-2 py-1.5 shadow-md">
            {pill('all', 'All stations')}
            {pill('harmonic', 'Harmonic only')}
            {pill('flood', 'Has flood data')}
            {pill('king', 'King tide today')}
            {loadingExtra && <span className="text-xs text-textSecondary self-center px-1">Loading…</span>}
          </div>
        </div>

        {/* Right station list panel — ~35% */}
        <div className="flex-[7] min-w-[280px] max-w-md flex flex-col bg-card border-l border-border">
          <div className="px-4 py-3 bg-ocean text-white">
            <div className="text-sm font-semibold">Stations in range · {radiusMiles} mi radius</div>
            <div className="text-xs text-white/70 mt-0.5">
              {saved?.name || 'Seattle, WA (default)'} · {visible.length} station{visible.length === 1 ? '' : 's'}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-borderLight">
            {visible.length === 0 && (
              <div className="px-4 py-6 text-sm text-textSecondary text-center">
                No stations match the current filter within {radiusMiles} miles.
              </div>
            )}
            {visible.map(s => {
              const isSelected = s.id === selectedId
              return (
                <button
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  className={`w-full text-left px-4 py-2.5 transition-colors hover:bg-surface ${
                    isSelected ? 'border-l-2 border-oceanLight bg-[#eaf4fb]' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-textPrimary truncate">{s.name}</div>
                      <div className="text-xs text-textSecondary">
                        #{s.id}
                        {s.distance_miles !== undefined && ` · ${s.distance_miles.toFixed(1)} mi`}
                        {s.harmonic ? <span className="ml-1 text-sea">H</span> : null}
                      </div>
                    </div>
                    <TideBadge station={s} />
                  </div>
                  {isSelected && sparkCurve.length > 1 && <Sparkline curve={sparkCurve} />}
                </button>
              )
            })}
          </div>

          <div className="p-3 border-t border-border">
            <a
              href={icsUrl(lat, lon, year, 'hilo,alerts,radius', radiusMiles)}
              download
              className="block w-full text-center py-2 px-4 bg-oceanLight text-white text-sm font-semibold rounded hover:bg-ocean transition-colors"
            >
              Download .ics ({radiusMiles} mi radius)
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
