import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import NavBar from '../components/NavBar'
import { fetchSpecialEvents, fetchStation, type Station } from '../api'
import type { FeedItem } from '../components/ComingUpFeed'
import { loadStation } from '../station-store'

const TYPE_STYLES = {
  alert:       { bg: '#fffaf0', border: '#e8c060', text: '#a06000', emoji: '⚠️' },
  opportunity: { bg: '#f4fbf7', border: '#a8dfc0', text: '#1a6640', emoji: '🦀' },
  info:        { bg: '#ffffff', border: '#e0e8f0', text: '#1b3a5c', emoji: '🌕' },
}

const TYPE_LABELS: Record<string, string> = {
  alert: 'Alert',
  opportunity: 'Opportunity',
  info: 'Informational',
}

function buildFeedItems(ev: Awaited<ReturnType<typeof fetchSpecialEvents>>): FeedItem[] {
  const items: FeedItem[] = []

  type PerigeanEvent = { date: string; moon_phase: string; description: string }
  type KingTideEvent = { date: string; time: string; time_12h: string; height_ft: number; extreme_type: string }
  type FloodEvent    = { date: string; flood_level: string; predicted_high_ft: number }
  type TidepoolEvent = { date: string; low_tide_time_12h: string; low_height_ft: number }

  for (const e of (ev.perigean_spring_tides as PerigeanEvent[] || [])) {
    items.push({ type: 'info', title: 'Perigean Spring Tide', date: e.date, description: e.description, detail: e.moon_phase })
  }
  for (const e of (ev.king_tides as KingTideEvent[] || [])) {
    if (e.extreme_type === 'king_tide') {
      items.push({ type: 'alert', title: 'King Tide', date: e.date, description: e.time_12h, detail: `${e.height_ft.toFixed(2)} ft` })
    } else if (e.extreme_type === 'extreme_low') {
      items.push({ type: 'opportunity', title: 'Extreme Low Tide', date: e.date, description: e.time_12h, detail: `${e.height_ft.toFixed(2)} ft` })
    }
  }
  for (const e of (ev.flood_risk as FloodEvent[] || [])) {
    items.push({ type: 'alert', title: `Flood Risk: ${e.flood_level}`, date: e.date, description: 'Predicted high:', detail: `${e.predicted_high_ft.toFixed(1)} ft` })
  }
  for (const e of (ev.tidepooling_windows as TidepoolEvent[] || [])) {
    items.push({ type: 'opportunity', title: 'Tidepooling Window', date: e.date, description: 'Low tide at', detail: `${e.low_tide_time_12h} (${e.low_height_ft.toFixed(1)} ft)` })
  }

  items.sort((a, b) => a.date.localeCompare(b.date))
  return items
}

export default function AlertsPage() {
  const [params] = useSearchParams()
  // Fall back to localStorage so the Alerts tab always works, even when
  // navigated directly from the NavBar without query params.
  const saved = loadStation()
  const stationId = params.get('station') ?? saved?.id ?? ''
  const year = Number(params.get('year') ?? saved?.year ?? new Date().getFullYear())

  const [station, setStation] = useState<Station | null>(null)
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!stationId) return
    fetchStation(stationId).then(setStation).catch(() => {})
  }, [stationId])

  useEffect(() => {
    if (!stationId) return
    setLoading(true)
    setError('')
    fetchSpecialEvents(stationId, year)
      .then(ev => setItems(buildFeedItems(ev)))
      .catch(() => setError('Could not load events. Is the FastAPI server running?'))
      .finally(() => setLoading(false))
  }, [stationId, year])

  const noStation = !stationId

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <div className="max-w-3xl mx-auto px-4 py-6">

        <div className="flex items-baseline justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold text-textPrimary">
              {station ? `Upcoming events — ${station.name}` : 'Upcoming events'}
            </h1>
            {station && (
              <p className="text-sm text-textSecondary mt-0.5">
                Station #{station.id} · {year}
              </p>
            )}
          </div>
          <Link to={stationId ? `/station/${stationId}` : '/'} className="text-sm text-oceanLight hover:underline">
            ← Back to dashboard
          </Link>
        </div>

        {noStation && (
          <div className="bg-card border border-border rounded p-6 text-center text-textSecondary text-sm">
            <p className="mb-2">No station selected.</p>
            <Link to="/" className="text-oceanLight hover:underline">Go to the dashboard to select a station →</Link>
          </div>
        )}

        {loading && (
          <div className="text-sm text-textSecondary py-8 text-center">Loading events…</div>
        )}

        {error && (
          <div className="bg-amberBg border border-amberBorder rounded p-3 text-sm text-amberText">
            {error}
          </div>
        )}

        {items && items.length === 0 && !loading && (
          <div className="bg-card border border-border rounded p-6 text-center text-textSecondary text-sm">
            No upcoming events found for {station?.name ?? 'this station'} in {year}.
          </div>
        )}

        {items && items.length > 0 && (
          <>
            {/* Legend */}
            <div className="flex gap-4 mb-3 text-xs text-textSecondary">
              {(['alert', 'opportunity', 'info'] as const).map(t => (
                <span key={t} className="flex items-center gap-1">
                  <span>{TYPE_STYLES[t].emoji}</span>
                  {TYPE_LABELS[t]}
                </span>
              ))}
            </div>

            <div className="space-y-2">
              {items.map((item, i) => {
                const s = TYPE_STYLES[item.type]
                return (
                  <div
                    key={i}
                    style={{ background: s.bg, borderLeftColor: s.border }}
                    className="border border-borderLight border-l-4 rounded px-4 py-3 flex items-start gap-3"
                  >
                    <span className="text-base mt-0.5 shrink-0">{s.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between gap-4">
                        <span className="text-sm font-semibold" style={{ color: s.text }}>
                          {item.title}
                        </span>
                        <span className="text-xs text-textSecondary shrink-0">{item.date}</span>
                      </div>
                      <p className="text-xs text-textSecondary mt-0.5">
                        {item.description}{item.detail && <strong> {item.detail}</strong>}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>

            <p className="text-xs text-textHint mt-4 text-center">
              {items.length} event{items.length !== 1 ? 's' : ''} · data from NOAA CO-OPS
            </p>
          </>
        )}
      </div>
    </div>
  )
}
