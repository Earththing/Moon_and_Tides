import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import NearbyStations from '../components/NearbyStations'
import type { Station, TideEvent } from '../api'

const STATIONS: Station[] = [
  { id: '9414290', name: 'San Francisco', lat: 37.8, lon: -122.4, state: 'CA', tidal: 1, harmonic: 1, distance_miles: 2.1, tidal_type: 'mixed' },
  { id: '9414750', name: 'Alameda', lat: 37.77, lon: -122.3, state: 'CA', tidal: 1, harmonic: 0, distance_miles: 8.4, tidal_type: 'mixed' },
]

const NORMAL_TIDE: TideEvent = {
  date: '2026-06-21', time: '06:00', time_12h: '6:00 AM', height_ft: 5.2, type: 'H'
}

describe('NearbyStations', () => {
  it('renders station names', () => {
    render(
      <NearbyStations
        stations={STATIONS}
        selectedId="9414290"
        onSelect={vi.fn()}
        currentTides={{ '9414290': NORMAL_TIDE, '9414750': null }}
      />
    )
    expect(screen.getByText('San Francisco')).toBeTruthy()
    expect(screen.getByText('Alameda')).toBeTruthy()
  })

  it('diurnal explanation card shown for diurnal station', () => {
    const diurnal: Station[] = [{ ...STATIONS[0], tidal_type: 'diurnal', mean_range_ft: 3.0 }]
    render(
      <NearbyStations
        stations={diurnal}
        selectedId="9414290"
        onSelect={vi.fn()}
        currentTides={{ '9414290': NORMAL_TIDE }}
      />
    )
    // The diurnal explanation card should be present (multiple "diurnal" occurrences expected)
    const matches = screen.getAllByText(/diurnal/i)
    expect(matches.length).toBeGreaterThan(0)
  })
})
