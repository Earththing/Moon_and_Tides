import { useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Circle, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { Station } from '../api'
import {
  type TideStatus, type ColorMode,
  markerColor, extremityColor, markerRadius, MAP_COLORS,
} from '../tide-status'

export interface MapStation extends Station {
  status: TideStatus | null
  highThresholdFt?: number
}

interface Props {
  center: [number, number]
  stations: MapStation[]
  selectedId: string
  onSelect: (id: string) => void
  radiusMiles: number
  colorMode: ColorMode
}

const MILES_TO_METERS = 1609.34

/** Re-center the map when the search location changes. */
function Recenter({ center, radiusMiles }: { center: [number, number]; radiusMiles: number }) {
  const map = useMap()
  useEffect(() => {
    // Fit the radius ring with a little margin
    const degPad = radiusMiles / 60 // ~1° lat ≈ 69 mi
    map.fitBounds([
      [center[0] - degPad, center[1] - degPad / Math.cos((center[0] * Math.PI) / 180)],
      [center[0] + degPad, center[1] + degPad / Math.cos((center[0] * Math.PI) / 180)],
    ])
  }, [map, center, radiusMiles])
  return null
}

function stationColor(s: MapStation, mode: ColorMode): string {
  if (!s.status) return MAP_COLORS.unknown
  if (mode === 'extremity') return extremityColor(s.status.todayMaxHighFt, s.highThresholdFt)
  return markerColor(s.status, mode)
}

const PHASE_LABEL: Record<string, string> = {
  high: 'at/near high', rising: 'rising ↑', low: 'at/near low', falling: 'falling ↓',
}

export default function CoastalMap({ center, stations, selectedId, onSelect, radiusMiles, colorMode }: Props) {
  return (
    <MapContainer center={center} zoom={9} className="h-full w-full" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      <Recenter center={center} radiusMiles={radiusMiles} />

      {/* Radius overlay: dashed sky-blue ring on the user location */}
      <Circle
        center={center}
        radius={radiusMiles * MILES_TO_METERS}
        pathOptions={{ color: '#5bbfde', dashArray: '8 8', fill: false, weight: 2 }}
      />

      {stations.map(s => {
        const color = stationColor(s, colorMode)
        const isSelected = s.id === selectedId
        return (
          <CircleMarker
            key={s.id}
            center={[s.lat, s.lon]}
            radius={markerRadius(s.status?.dailyRangeFt ?? 0)}
            pathOptions={{
              color: isSelected ? '#1b3a5c' : '#ffffff',
              weight: isSelected ? 3 : 1.5,
              fillColor: color,
              fillOpacity: 0.85,
            }}
            eventHandlers={{ click: () => onSelect(s.id) }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              <div className="text-xs">
                <div className="font-semibold">{s.name}</div>
                {s.status?.heightFt != null && (
                  <div>
                    {s.status.heightFt.toFixed(1)} ft · {s.status.phase ? PHASE_LABEL[s.status.phase] : ''}
                  </div>
                )}
                {s.status?.nextEvent && (
                  <div>
                    Next: {s.status.nextEvent.type === 'H' ? 'high' : 'low'}{' '}
                    {s.status.nextEvent.time_12h} · {s.status.nextEvent.height_ft.toFixed(1)} ft
                  </div>
                )}
                {s.status?.kingTide && <div className="font-semibold">⚠ King tide today</div>}
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
