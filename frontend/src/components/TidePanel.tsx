import type { Station, TideEvent } from '../api'
import type { CalOptions } from '../types'
import TideEventList from './TideEventList'
import CalendarOptions from './CalendarOptions'
import AlertRadiusSlider from './AlertRadiusSlider'
import DownloadButton from './DownloadButton'

interface Props {
  station: Station | null
  todayEvents: TideEvent[]
  lat: number
  lon: number
  year: number
  options: CalOptions
  onOptionsChange: (o: CalOptions) => void
  radiusMiles: number
  onRadiusChange: (v: number) => void
  radiusStationCount: number
}

function Divider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 my-2">
      <div className="flex-1 border-t border-borderLight" />
      <span className="text-xs font-semibold uppercase tracking-wide text-textHint">{label}</span>
      <div className="flex-1 border-t border-borderLight" />
    </div>
  )
}

export default function TidePanel({
  station, todayEvents, lat, lon, year,
  options, onOptionsChange, radiusMiles, onRadiusChange, radiusStationCount,
}: Props) {
  const isHarmonic = station?.harmonic === 1
  const hasFloodData = station?.has_flood_thresholds ?? false
  const radiusActive = radiusMiles > 10

  return (
    <div className="bg-card border border-border rounded p-3 space-y-1">
      <Divider label="Today's tides" />
      {todayEvents.length > 0
        ? <TideEventList events={todayEvents} />
        : <p className="text-xs text-textHint py-2">No tide data for today.</p>
      }

      <Divider label="Calendar options" />
      <CalendarOptions
        options={options}
        onChange={onOptionsChange}
        isHarmonic={isHarmonic}
        hasFloodData={hasFloodData}
        radiusActive={radiusActive}
      />

      <Divider label="Alert radius" />
      <AlertRadiusSlider
        value={radiusMiles}
        stationCount={radiusStationCount}
        onChange={onRadiusChange}
      />

      <div className="pt-2">
        <DownloadButton
          stationId={station?.id ?? ''}
          lat={lat} lon={lon} year={year} options={options}
        />
      </div>
    </div>
  )
}
