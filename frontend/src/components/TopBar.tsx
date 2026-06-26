interface Props {
  stationName: string
  stationId: string
  view: 'day' | 'week' | 'month' | 'year'
  onViewChange: (v: 'day' | 'week' | 'month' | 'year') => void
}

const VIEWS: Array<{ key: 'day' | 'week' | 'month' | 'year'; label: string }> = [
  { key: 'day', label: 'Day' },
  { key: 'week', label: 'Week' },
  { key: 'month', label: 'Month' },
  { key: 'year', label: 'Year' },
]

export default function TopBar({ stationName, stationId, view, onViewChange }: Props) {
  return (
    <div className="bg-card border-b border-border px-4 py-2 flex items-center justify-between">
      <div>
        <span className="font-semibold text-textPrimary">{stationName}</span>
        {stationId && (
          <span className="ml-2 text-sm text-textSecondary">#{stationId}</span>
        )}
      </div>
      <div className="flex gap-1">
        {VIEWS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => onViewChange(key)}
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
