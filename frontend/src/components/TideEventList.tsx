import type { TideEvent } from '../api'

interface Props {
  events: TideEvent[]
  currentTime?: string  // HH:MM — highlights the nearest event
}

function isCurrentEvent(event: TideEvent, now: string): boolean {
  // Highlight the event whose time is closest to now and hasn't passed yet by more than 2 hours
  return event.time <= now && now <= event.time.replace(/(\d{2})/, h => String(Number(h) + 2).padStart(2, '0'))
}

export default function TideEventList({ events, currentTime }: Props) {
  const now = currentTime ?? new Date().toTimeString().slice(0, 5)

  return (
    <div className="space-y-0.5">
      {events.map((ev, i) => {
        const isCurrent = isCurrentEvent(ev, now)
        return (
          <div
            key={i}
            className={`flex items-center gap-2 px-2 py-1.5 rounded text-sm border ${
              isCurrent
                ? 'bg-[#e5f4fb] border-sky/30'
                : 'bg-transparent border-transparent'
            }`}
          >
            <span className="w-[52px] tabular-nums text-textSecondary shrink-0">
              {ev.time_12h}
            </span>
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                ev.type === 'H' ? 'bg-oceanLight' : 'bg-sea'
              }`}
            />
            <span className={`flex-1 ${isCurrent ? 'text-oceanLight font-semibold' : 'text-textPrimary'}`}>
              {ev.type === 'H' ? 'High Tide' : 'Low Tide'}
            </span>
            <span className="tabular-nums font-medium text-textPrimary">
              {ev.height_ft.toFixed(2)} ft
            </span>
          </div>
        )
      })}
    </div>
  )
}
