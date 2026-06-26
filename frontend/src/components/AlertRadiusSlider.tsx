interface Props {
  value: number
  stationCount: number
  onChange: (v: number) => void
}

export default function AlertRadiusSlider({ value, stationCount, onChange }: Props) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-textSecondary">
        <span>Alert radius</span>
        <span className="font-medium text-textPrimary">
          {value} mi · {stationCount} station{stationCount !== 1 ? 's' : ''}
        </span>
      </div>
      <input
        type="range"
        min={10}
        max={150}
        step={5}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-oceanLight"
      />
    </div>
  )
}
