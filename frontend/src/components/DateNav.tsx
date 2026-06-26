interface Props {
  date: string
  isToday: boolean
  view: 'day' | 'week' | 'month' | 'year'
  showDayNight: boolean
  onToggleDayNight: () => void
  onPrev: () => void
  onNext: () => void
  onDateChange: (d: string) => void
  onToday: () => void
}

function rangeLabel(date: string, view: 'day' | 'week' | 'month' | 'year'): string {
  const d = new Date(date + 'T12:00:00')
  switch (view) {
    case 'day':
      return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
    case 'week': {
      const end = new Date(d)
      end.setDate(end.getDate() + 6)
      const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
      return `${d.toLocaleDateString('en-US', opts)} – ${end.toLocaleDateString('en-US', { ...opts, year: 'numeric' })}`
    }
    case 'month':
      return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    case 'year':
      return String(d.getFullYear())
  }
}

export default function DateNav({
  date, isToday, view, showDayNight,
  onToggleDayNight, onPrev, onNext, onDateChange, onToday,
}: Props) {
  return (
    <div className="flex items-center gap-2 px-4 py-1.5 bg-card border-b border-border flex-wrap">
      <button
        onClick={onPrev}
        className="px-2 py-1 text-sm text-textSecondary hover:text-textPrimary hover:bg-surface rounded border border-border"
        title={`Previous ${view}`}
      >
        ←
      </button>

      <span className="text-sm font-medium text-textPrimary min-w-[200px] text-center">
        {rangeLabel(date, view)}
      </span>

      <button
        onClick={onNext}
        className="px-2 py-1 text-sm text-textSecondary hover:text-textPrimary hover:bg-surface rounded border border-border"
        title={`Next ${view}`}
      >
        →
      </button>

      {view === 'day' && (
        <input
          type="date"
          value={date}
          onChange={e => e.target.value && onDateChange(e.target.value)}
          className="text-xs px-2 py-1 border border-border rounded text-textSecondary bg-white focus:outline-none focus:border-oceanLight"
        />
      )}

      {!isToday && (
        <button
          onClick={onToday}
          className="px-3 py-1 text-xs font-medium text-oceanLight border border-oceanLight rounded hover:bg-oceanLight hover:text-white transition-colors"
        >
          Today
        </button>
      )}

      {view !== 'year' && (
        <button
          onClick={onToggleDayNight}
          title={
            view === 'day'
              ? 'Toggle day/night shading with sunrise/sunset gradient'
              : 'Toggle day/night shading — darker bands = night hours'
          }
          className={`ml-auto px-3 py-1 text-xs font-medium rounded border transition-colors ${
            showDayNight
              ? 'bg-[#0a152a] text-white border-[#0a152a]'
              : 'text-textSecondary border-border hover:border-textSecondary'
          }`}
        >
          {showDayNight ? '🌙 Night on' : '🌙 Night off'}
        </button>
      )}
    </div>
  )
}
