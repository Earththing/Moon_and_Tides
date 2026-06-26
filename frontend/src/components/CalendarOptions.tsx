import type { CalOptions as Options } from '../types'

interface Props {
  options: Options
  onChange: (opts: Options) => void
  isHarmonic: boolean
  hasFloodData: boolean
  radiusActive: boolean
}

interface Item {
  key: keyof Options
  label: string
  locked?: boolean
  disabledWhen?: boolean
  disabledTip?: string
}

const ITEMS: Item[] = [
  { key: 'hilo', label: 'High & low tides', locked: true },
  { key: 'alerts', label: 'King tide alerts' },
  { key: 'perigean', label: 'Perigean spring tides' },
  { key: 'slack', label: 'Slack water', disabledWhen: true, disabledTip: 'Requires a harmonic station' },
  { key: 'tidepooling', label: 'Tidepooling windows', disabledWhen: true, disabledTip: 'Requires a harmonic station' },
  { key: 'flood', label: 'Flood risk', disabledWhen: true, disabledTip: 'No NOAA flood thresholds for this station' },
  { key: 'radius', label: 'Radius alerts', disabledWhen: true, disabledTip: 'Set alert radius above 10 miles' },
]

export default function CalendarOptions({ options, onChange, isHarmonic, hasFloodData, radiusActive }: Props) {
  function isDisabled(item: Item): boolean {
    if (item.locked) return false
    if ((item.key === 'slack' || item.key === 'tidepooling') && !isHarmonic) return true
    if (item.key === 'flood' && !hasFloodData) return true
    if (item.key === 'radius' && !radiusActive) return true
    return false
  }

  function tipFor(item: Item): string | undefined {
    if ((item.key === 'slack' || item.key === 'tidepooling') && !isHarmonic) return item.disabledTip
    if (item.key === 'flood' && !hasFloodData) return item.disabledTip
    if (item.key === 'radius' && !radiusActive) return item.disabledTip
    return undefined
  }

  return (
    <div className="space-y-1">
      {ITEMS.map(item => {
        const disabled = isDisabled(item)
        const tip = tipFor(item)
        return (
          <label
            key={item.key}
            title={tip}
            className={`flex items-center gap-2 text-sm select-none ${
              disabled ? 'cursor-not-allowed text-textHint' : 'cursor-pointer text-textPrimary'
            }`}
          >
            <input
              type="checkbox"
              checked={item.locked ? true : options[item.key]}
              disabled={item.locked || disabled}
              onChange={e => {
                if (item.locked || disabled) return
                onChange({ ...options, [item.key]: e.target.checked })
              }}
              className="accent-oceanLight"
            />
            {item.label}
            {item.locked && (
              <span className="text-xs text-textHint">(always included)</span>
            )}
          </label>
        )
      })}
    </div>
  )
}
