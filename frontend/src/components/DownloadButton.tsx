import { useEffect, useState } from 'react'
import { icsUrl } from '../api'

interface Props {
  stationId: string
  lat: number
  lon: number
  year: number
  options: Record<string, boolean>
}

interface Counts {
  hilo_high?: number
  hilo_low?: number
  king_tide?: number
  extreme_low?: number
  perigean?: number
  flood_risk?: number
  tidepooling?: number
  slack_water?: number
  radius_alert?: number
}

const LABELS: Record<string, string> = {
  hilo_high:    '🌊 High tides',
  hilo_low:     '🏖 Low tides',
  king_tide:    '⚠️ King tides',
  extreme_low:  '⚠️ Extreme lows',
  perigean:     '🌕 Perigean spring tides',
  flood_risk:   '🚨 Flood risk days',
  tidepooling:  '🦀 Tidepooling windows',
  slack_water:  '⚓ Slack water',
  radius_alert: '🌊 Nearby alerts',
}

export default function DownloadButton({ stationId, lat, lon, year, options }: Props) {
  const [counts, setCounts] = useState<Counts | null>(null)
  const [total, setTotal] = useState<number | null>(null)
  const [open, setOpen] = useState(false)

  const optStr = Object.entries(options).filter(([, v]) => v).map(([k]) => k).join(',') || 'hilo'
  const href = icsUrl(lat, lon, year, optStr)

  useEffect(() => {
    if (!stationId) return
    const params = new URLSearchParams({
      station_id: stationId,
      year: String(year),
      lat: String(lat),
      lon: String(lon),
      options: optStr,
    })
    fetch(`/api/v1/ics-preview?${params}`)
      .then(r => r.json())
      .then(d => { setCounts(d.counts); setTotal(d.total) })
      .catch(() => { setCounts(null); setTotal(null) })
  }, [stationId, year, lat, lon, optStr])

  return (
    <div className="space-y-1">
      <a
        href={href}
        download
        className="block w-full text-center py-2 px-4 bg-oceanLight text-white text-sm font-semibold rounded hover:bg-ocean transition-colors"
      >
        Download .ics ({year}){total !== null ? ` · ${total.toLocaleString()} events` : ''}
      </a>

      {counts && Object.keys(counts).length > 0 && (
        <div>
          <button
            onClick={() => setOpen(v => !v)}
            className="text-xs text-textSecondary hover:text-textPrimary w-full text-center"
          >
            {open ? '▲ Hide breakdown' : '▼ Show event breakdown'}
          </button>
          {open && (
            <div className="mt-1 rounded border border-borderLight bg-surface text-xs divide-y divide-borderLight">
              {(Object.entries(LABELS) as [string, string][])
                .filter(([k]) => (counts as Record<string, number>)[k] > 0)
                .map(([k, label]) => (
                  <div key={k} className="flex justify-between px-2 py-1">
                    <span className="text-textSecondary">{label}</span>
                    <span className="font-medium tabular-nums">
                      {((counts as Record<string, number>)[k]).toLocaleString()}
                    </span>
                  </div>
                ))
              }
            </div>
          )}
        </div>
      )}
    </div>
  )
}
