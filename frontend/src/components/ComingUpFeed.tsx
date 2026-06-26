interface FeedItem {
  type: 'alert' | 'opportunity' | 'info'
  title: string
  description: string
  detail?: string
  date: string
}

interface Props {
  items: FeedItem[]
  onViewAll?: () => void
}

const MAX_ITEMS = 6

const TYPE_STYLES = {
  alert: {
    bg: '#fffaf0',
    border: '#e8c060',
    text: '#a06000',
    emoji: '⚠️',
  },
  opportunity: {
    bg: '#f4fbf7',
    border: '#a8dfc0',
    text: '#1a6640',
    emoji: '🦀',
  },
  info: {
    bg: '#ffffff',
    border: '#e0e8f0',
    text: '#1b3a5c',
    emoji: '⚓',
  },
}

export default function ComingUpFeed({ items, onViewAll }: Props) {
  if (items.length === 0) return null

  const visible = items.slice(0, MAX_ITEMS)
  const hasMore = items.length > MAX_ITEMS

  return (
    <div className="bg-card border border-border rounded overflow-hidden">
      <div className="px-3 py-2 bg-ocean text-white text-xs font-semibold uppercase tracking-wide">
        Coming up
      </div>
      <div className="p-2 space-y-2">
        {visible.map((item, i) => {
          const s = TYPE_STYLES[item.type]
          return (
            <div
              key={i}
              style={{ background: s.bg, borderColor: s.border }}
              className="border-l-2 rounded px-2 py-1.5"
            >
              <div className="text-xs font-semibold" style={{ color: s.text }}>
                {s.emoji} {item.title}
              </div>
              <div className="text-xs text-textSecondary mt-0.5">{item.date}</div>
              <div className="text-xs text-textSecondary mt-0.5 leading-snug">
                {item.description}
                {item.detail && <strong> {item.detail}</strong>}
              </div>
            </div>
          )
        })}
        {hasMore && (
          <button
            onClick={onViewAll}
            className="text-xs text-oceanLight hover:underline w-full text-right pt-1"
          >
            View all {items.length} events →
          </button>
        )}
      </div>
    </div>
  )
}

export type { FeedItem }
