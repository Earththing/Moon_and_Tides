import type { Station, TideEvent } from '../api'

interface Props {
  stations: Station[]
  selectedId: string
  onSelect: (id: string) => void
  currentTides: Record<string, TideEvent | null>
}

function TideBadge({ tide, isAlert }: { tide: TideEvent | null; isAlert?: boolean }) {
  if (!tide) return null
  const dir = tide.type === 'H' ? '↑' : '↓'
  if (isAlert) {
    return (
      <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-amberBg text-amberText border border-amberBorder">
        ⚠ {dir} {tide.height_ft.toFixed(1)} ft
      </span>
    )
  }
  const cls = tide.type === 'H'
    ? 'bg-[#eaf4fb] text-oceanLight'
    : 'bg-[#e8f6ef] text-sea'
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${cls}`}>
      {dir} {tide.height_ft.toFixed(1)} ft
    </span>
  )
}

export default function NearbyStations({ stations, selectedId, onSelect, currentTides }: Props) {
  return (
    <div className="bg-card border border-border rounded overflow-hidden">
      <div className="px-3 py-2 bg-ocean text-white text-xs font-semibold uppercase tracking-wide">
        Nearby Stations
      </div>
      <div className="divide-y divide-borderLight">
        {stations.map(s => {
          const tide = currentTides[s.id] ?? null
          const isSelected = s.id === selectedId
          return (
            <button
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`w-full text-left px-3 py-2 transition-colors hover:bg-surface ${
                isSelected ? 'border-l-2 border-oceanLight bg-[#eaf4fb]' : ''
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-textPrimary truncate">{s.name}</div>
                  <div className="text-xs text-textSecondary">
                    #{s.id}
                    {s.distance_miles !== undefined && ` · ${s.distance_miles.toFixed(1)} mi`}
                    {s.harmonic ? (
                      <span className="ml-1 text-sea">H</span>
                    ) : null}
                  </div>
                </div>
                <TideBadge tide={tide} />
              </div>
            </button>
          )
        })}
      </div>

      {stations.length > 0 && (() => {
        const sel = stations.find(s => s.id === selectedId)
        if (!sel) return null
        return (
          <div className="border-t border-border px-3 py-2 space-y-1">
            <div className="text-xs font-semibold text-textSecondary uppercase tracking-wide mb-1">
              Station stats
            </div>
            {sel.mean_range_ft != null && (
              <div className="flex justify-between text-xs">
                <span className="text-textSecondary">Tidal range</span>
                <span className="font-medium">{sel.mean_range_ft.toFixed(1)} ft</span>
              </div>
            )}
            {sel.tidal_type && (
              <div className="flex justify-between text-xs">
                <span className="text-textSecondary">Tidal type</span>
                <span className="font-medium capitalize">{sel.tidal_type}</span>
              </div>
            )}
            <div className="flex justify-between text-xs">
              <span className="text-textSecondary">Datum</span>
              <span className="font-medium">MLLW</span>
            </div>
            {sel.tidal_type === 'diurnal' && (
              <div className="mt-2 p-2 bg-[#eaf4fb] border border-sky/30 rounded text-xs text-textPrimary leading-relaxed">
                This station has a <strong>diurnal</strong> tidal pattern — one high and one low
                tide per day, instead of the two-per-day pattern common on the East Coast.
                This occurs because of the station's location relative to the moon's orbital path.
              </div>
            )}
          </div>
        )
      })()}
    </div>
  )
}
