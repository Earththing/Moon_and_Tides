import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  fetchNearestStations, fetchStation, fetchTidesDay,
  fetchYearSummary, fetchSpecialEvents,
  type Station, type TideEvent, type CurvePoint,
} from '../api'
import type { CalOptions } from '../types'
import NavBar from '../components/NavBar'
import TopBar from '../components/TopBar'
import TideCurveChart from '../components/TideCurveChart'
import NearbyStations from '../components/NearbyStations'
import TidePanel from '../components/TidePanel'
import ComingUpFeed, { type FeedItem } from '../components/ComingUpFeed'
import LocationSearch from '../components/LocationSearch'

const DEFAULT_LAT = 47.6062
const DEFAULT_LON = -122.3321
const CURRENT_YEAR = new Date().getFullYear()


function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export default function Dashboard() {
  const { stationId: paramStation, year: paramYear } = useParams<{ stationId?: string; year?: string }>()
  const navigate = useNavigate()

  const [lat, setLat] = useState(DEFAULT_LAT)
  const [lon, setLon] = useState(DEFAULT_LON)
  const [searchedLocation, setSearchedLocation] = useState('')
  const [stations, setStations] = useState<Station[]>([])
  const [selectedId, setSelectedId] = useState(paramStation ?? '')
  const [selectedStation, setSelectedStation] = useState<Station | null>(null)
  const [view, setView] = useState<'day' | 'week' | 'month' | 'year'>('day')
  const [year] = useState(paramYear ? Number(paramYear) : CURRENT_YEAR)
  const [todayEvents, setTodayEvents] = useState<TideEvent[]>([])
  const [curveData, setCurveData] = useState<CurvePoint[]>([])
  const [monthlyHigh, setMonthlyHigh] = useState<(number | null)[] | undefined>()
  const [monthlyLow, setMonthlyLow] = useState<(number | null)[] | undefined>()
  const [feedItems, setFeedItems] = useState<FeedItem[]>([])
  const [radiusMiles, setRadiusMiles] = useState(50)
  const [radiusStations, setRadiusStations] = useState<Station[]>([])
  const [options, setOptions] = useState<CalOptions>({
    hilo: true, alerts: true, slack: false, tidepooling: false,
    flood: false, perigean: true, radius: false,
  })

  // Load nearby stations on location change — always select the nearest
  useEffect(() => {
    fetchNearestStations(lat, lon, 5).then(list => {
      setStations(list)
      // Auto-select nearest unless the URL specified a station (paramStation)
      if (list.length > 0 && !paramStation) {
        setSelectedId(list[0].id)
      } else if (list.length > 0 && !selectedId) {
        setSelectedId(list[0].id)
      }
    }).catch(console.error)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lat, lon])

  // Load selected station detail
  useEffect(() => {
    if (!selectedId) return
    fetchStation(selectedId).then(setSelectedStation).catch(console.error)
  }, [selectedId])

  // Load today's tides + curve
  useEffect(() => {
    if (!selectedId) return
    fetchTidesDay(selectedId, todayStr()).then(({ hilo, curve }) => {
      setTodayEvents(hilo)
      setCurveData(curve)
    }).catch(console.error)
  }, [selectedId])

  // Load year summary for year view
  useEffect(() => {
    if (!selectedId || view !== 'year') return
    fetchYearSummary(selectedId, year).then(s => {
      setMonthlyHigh(s.monthly_mean_high)
      setMonthlyLow(s.monthly_mean_low)
    }).catch(console.error)
  }, [selectedId, year, view])

  // Load special events for feed
  useEffect(() => {
    if (!selectedId) return
    fetchSpecialEvents(selectedId, year, lat, lon).then(ev => {
      const items: FeedItem[] = []

      type PerigeanEvent = { date: string; moon_phase: string; description: string }
      type KingTideEvent = { date: string; time: string; time_12h: string; height_ft: number; extreme_type: string }
      type FloodEvent = { date: string; flood_level: string; predicted_high_ft: number }
      type TidepoolEvent = { date: string; low_tide_time_12h: string; low_height_ft: number }

      for (const e of (ev.perigean_spring_tides as PerigeanEvent[] || [])) {
        items.push({ type: 'info', title: 'Perigean Spring Tide', date: e.date, description: e.description, detail: e.moon_phase })
      }
      for (const e of (ev.king_tides as KingTideEvent[] || [])) {
        if (e.extreme_type === 'king_tide') {
          items.push({ type: 'alert', title: 'King Tide', date: e.date, description: `${e.time_12h}`, detail: `${e.height_ft.toFixed(2)} ft` })
        }
      }
      for (const e of (ev.flood_risk as FloodEvent[] || [])) {
        items.push({ type: 'alert', title: `Flood Risk: ${e.flood_level}`, date: e.date, description: `Predicted high:`, detail: `${e.predicted_high_ft.toFixed(1)} ft` })
      }
      for (const e of (ev.tidepooling_windows as TidepoolEvent[] || [])) {
        items.push({ type: 'opportunity', title: 'Tidepooling Window', date: e.date, description: `Low tide at`, detail: `${e.low_tide_time_12h} (${e.low_height_ft.toFixed(1)} ft)` })
      }

      items.sort((a, b) => a.date.localeCompare(b.date))
      setFeedItems(items)
    }).catch(console.error)
  }, [selectedId, year, lat, lon])

  // Radius stations
  useEffect(() => {
    if (radiusMiles <= 10) { setRadiusStations([]); return }
    // Reuse already loaded list filtered by distance
    setRadiusStations(stations.filter(s => (s.distance_miles ?? 0) <= radiusMiles))
  }, [radiusMiles, stations])

  function handleStationSelect(id: string) {
    setSelectedId(id)
    navigate(`/station/${id}`, { replace: true })
  }

  const currentTides: Record<string, TideEvent | null> = {}
  for (const s of stations) {
    const now = new Date().toTimeString().slice(0, 5)
    const past = todayEvents.filter(() => s.id === selectedId)
    const nearest = past.findLast(e => e.time <= now) ?? past[0] ?? null
    currentTides[s.id] = nearest
  }

  const hasFeed = feedItems.length > 0

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <NavBar />

      <div className="px-4 py-2 bg-card border-b border-border">
        <div className="max-w-screen-xl mx-auto">
          <LocationSearch
            onSelect={r => {
              setLat(r.lat)
              setLon(r.lon)
              // Store first two parts of display name, e.g. "Edmonds, Snohomish County"
              setSearchedLocation(r.display_name.split(',').slice(0, 2).join(',').trim())
            }}
            placeholder="Search city or address…"
          />
        </div>
      </div>

      <TopBar
        stationName={selectedStation?.name ?? '…'}
        stationId={selectedId}
        searchedLocation={searchedLocation}
        distanceMiles={stations.find(s => s.id === selectedId)?.distance_miles}
        view={view}
        onViewChange={setView}
      />

      <div className="max-w-screen-xl mx-auto w-full px-4 py-3 space-y-3">
        {/* Tide curve */}
        <TideCurveChart
          curveData={curveData}
          hiloData={todayEvents}
          floodMinor={selectedStation?.flood_minor_ft ?? undefined}
          view={view}
          stationId={selectedId}
          monthlyMeanHigh={monthlyHigh}
          monthlyMeanLow={monthlyLow}
        />

        {/* Three-column (or two-column) grid */}
        <div
          className={`grid gap-3 items-start ${
            hasFeed ? 'grid-cols-[220px_1fr_200px]' : 'grid-cols-[220px_1fr]'
          }`}
        >
          {/* Left: nearby stations */}
          <NearbyStations
            stations={stations}
            selectedId={selectedId}
            onSelect={handleStationSelect}
            currentTides={currentTides}
          />

          {/* Middle: tide panel */}
          <TidePanel
            station={selectedStation}
            todayEvents={todayEvents}
            lat={lat}
            lon={lon}
            year={year}
            options={options}
            onOptionsChange={setOptions}
            radiusMiles={radiusMiles}
            onRadiusChange={setRadiusMiles}
            radiusStationCount={radiusStations.length}
          />

          {/* Right: feed (only if content) */}
          {hasFeed && (
            <ComingUpFeed
              items={feedItems}
              onViewAll={() => navigate(`/alerts?station=${selectedId}&year=${year}`)}
            />
          )}
        </div>
      </div>
    </div>
  )
}
