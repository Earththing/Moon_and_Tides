import { useState, useEffect, useRef } from 'react'
import { geocode, type GeocodeResult } from '../api'

interface Props {
  onSelect: (result: GeocodeResult) => void
  placeholder?: string
}

export default function LocationSearch({ onSelect, placeholder = 'Search location…' }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodeResult[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    if (query.length < 3) { setResults([]); setOpen(false); return }
    timer.current = setTimeout(async () => {
      setLoading(true)
      try {
        const r = await geocode(query)
        setResults(r.slice(0, 4))
        setOpen(r.length > 0)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => { if (timer.current) clearTimeout(timer.current) }
  }, [query])

  function pick(r: GeocodeResult) {
    setQuery(r.display_name.split(',').slice(0, 2).join(','))
    setOpen(false)
    onSelect(r)
  }

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-border rounded text-sm bg-white focus:outline-none focus:border-oceanLight"
      />
      {loading && (
        <span className="absolute right-3 top-2.5 text-xs text-textHint">…</span>
      )}
      {open && results.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-border rounded shadow-lg">
          {results.map((r, i) => (
            <li key={i}>
              <button
                className="w-full text-left px-3 py-2 text-sm text-textPrimary hover:bg-surface truncate"
                onMouseDown={() => pick(r)}
              >
                {r.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
