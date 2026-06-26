interface Props {
  stationName: string
  stationId: string
  searchedLocation?: string
  distanceMiles?: number
  view: 'day' | 'week' | 'month' | 'year'
  onViewChange: (v: 'day' | 'week' | 'month' | 'year') => void
}

const VIEWS: Array<{
  key: 'day' | 'week' | 'month' | 'year'
  label: string
  title: string
}> = [
  { key: 'day',   label: 'Day',   title: 'Detailed 6-minute tide curve for a single day' },
  { key: 'week',  label: 'Week',  title: 'High & low tides across 7 days' },
  { key: 'month', label: 'Month', title: 'High & low tides for the full month' },
  { key: 'year',  label: 'Year',  title: 'Monthly average high & low tides for the year' },
]

export default function TopBar({ stationName, stationId, searchedLocation, distanceMiles, view, onViewChange }: Props) {
  const showNearest = searchedLocation && stationName
    && searchedLocation.split(',')[0].trim().toLowerCase() !== stationName.toLowerCase()

  return (
    <div className="bg-card border-b border-border px-4 py-2 flex items-center justify-between flex-wrap gap-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-semibold text-textPrimary">{stationName}</span>
        {stationId && (
          <span className="text-sm text-textSecondary">#{stationId}</span>
        )}
        {showNearest && (
          <span className="text-xs text-amberText bg-amberBg border border-amberBorder rounded px-2 py-0.5">
            No NOAA station at {searchedLocation.split(',')[0]} —
            nearest is {stationName}{distanceMiles !== undefined ? ` (${distanceMiles.toFixed(0)} mi away)` : ''}
          </span>
        )}
      </div>
      <div className="flex gap-1">
        {VIEWS.map(({ key, label, title }) => (
          <button
            key={key}
            onClick={() => onViewChange(key)}
            title={title}
            className={`px-3 py-1 rounded text-sm font-medium border transition-colors ${
              view === key
                ? 'bg-oceanLight text-white border-oceanLight'
                : 'bg-white text-textSecondary border-border hover:border-oceanLight hover:text-oceanLight'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
