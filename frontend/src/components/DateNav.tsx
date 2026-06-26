interface Props {
  date: string            // YYYY-MM-DD
  isToday: boolean
  onPrev: () => void
  onNext: () => void
  onDateChange: (d: string) => void
  onToday: () => void
}

export default function DateNav({ date, isToday, onPrev, onNext, onDateChange, onToday }: Props) {
  const label = new Date(date + 'T12:00:00').toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  })

  return (
    <div className="flex items-center gap-2 px-4 py-1.5 bg-card border-b border-border">
      <button
        onClick={onPrev}
        className="px-2 py-1 text-sm text-textSecondary hover:text-textPrimary hover:bg-surface rounded border border-border"
        title="Previous day"
      >
        ←
      </button>

      <span className="text-sm font-medium text-textPrimary min-w-[180px] text-center">
        {label}
      </span>

      <button
        onClick={onNext}
        className="px-2 py-1 text-sm text-textSecondary hover:text-textPrimary hover:bg-surface rounded border border-border"
        title="Next day"
      >
        →
      </button>

      <input
        type="date"
        value={date}
        onChange={e => e.target.value && onDateChange(e.target.value)}
        className="text-xs px-2 py-1 border border-border rounded text-textSecondary bg-white focus:outline-none focus:border-oceanLight"
      />

      {!isToday && (
        <button
          onClick={onToday}
          className="px-3 py-1 text-xs font-medium text-oceanLight border border-oceanLight rounded hover:bg-oceanLight hover:text-white transition-colors"
        >
          Today
        </button>
      )}
    </div>
  )
}
