import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import DownloadButton from '../components/DownloadButton'

const BASE_OPTS = { hilo: true, alerts: true, slack: false, tidepooling: false, flood: false, perigean: false, radius: false }

describe('DownloadButton', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve({ counts: {}, total: 0 }) })))
  })

  // This test used to assert the URL contained lat/lon. That was the bug: the
  // lat/lon route serves the station nearest the point, not the one selected.
  // The URL must name the station.
  it('constructs correct ICS URL from station, year, options', () => {
    render(<DownloadButton stationId="9447427" year={2026} options={BASE_OPTS} radiusMiles={50} />)
    const link = screen.getByRole('link') as HTMLAnchorElement
    // jsdom doesn't encode commas in href; check the raw attribute instead
    expect(link.getAttribute('href')).toBe('/calendar/2026/station/9447427.ics?options=hilo,alerts')
    expect(link.getAttribute('download')).toBeDefined()
  })

  it('passes the slider radius when radius alerts are on', () => {
    render(<DownloadButton stationId="9447427" year={2027} options={{ ...BASE_OPTS, radius: true }} radiusMiles={40} />)
    const href = screen.getByRole('link').getAttribute('href')
    expect(href).toBe('/calendar/2027/station/9447427.ics?options=hilo,alerts,radius&radius_miles=40')
  })
})
