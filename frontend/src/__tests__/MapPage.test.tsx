import { describe, expect, test, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import MapPage from '../pages/MapPage'

// Leaflet needs a real layout engine — replace the map with a marker-count stub.
vi.mock('../components/CoastalMap', () => ({
  default: ({ stations }: { stations: { id: string }[] }) => (
    <div data-testid="coastal-map">{stations.length} markers</div>
  ),
}))

const STATIONS = [
  { id: '9447130', name: 'Seattle', lat: 47.60, lon: -122.34, state: 'WA', tidal: 1, harmonic: 1, distance_miles: 0.5 },
  { id: '9445958', name: 'Bremerton', lat: 47.56, lon: -122.62, state: 'WA', tidal: 1, harmonic: 0, distance_miles: 13.2 },
]

const HILO = [
  { date: '2026-06-21', time: '03:15', time_12h: '3:15 AM', height_ft: 8.2, type: 'H' },
  { date: '2026-06-21', time: '09:30', time_12h: '9:30 AM', height_ft: 0.8, type: 'L' },
]

function mockFetch(url: string): Promise<Response> {
  const respond = (body: unknown) =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(body) } as Response)
  if (url.includes('/stations/radius')) return respond(STATIONS)
  if (url.includes('/map/status')) {
    return respond({
      stations: {
        '9447130': { hilo: HILO, high_threshold_ft: 8.0 },
        '9445958': { hilo: HILO.map(h => ({ ...h, height_ft: h.height_ft - 2 })), high_threshold_ft: 8.0 },
      },
    })
  }
  if (url.includes('/tides/day')) return respond({ hilo: HILO, curve: [] })
  return respond({})
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn((url: string) => mockFetch(url)))
  localStorage.clear()
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/map']}>
      <MapPage />
    </MemoryRouter>,
  )
}

describe('MapPage', () => {
  test('renders stations in the right panel with header count', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Seattle')).toBeInTheDocument())
    expect(screen.getByText('Bremerton')).toBeInTheDocument()
    expect(screen.getByText(/Stations in range · 50 mi radius/)).toBeInTheDocument()
    expect(screen.getByTestId('coastal-map')).toHaveTextContent('2 markers')
  })

  test('harmonic filter hides non-harmonic stations', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Bremerton')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Harmonic only' }))
    expect(screen.queryByText('Bremerton')).not.toBeInTheDocument()
    expect(screen.getByText('Seattle')).toBeInTheDocument()
    expect(screen.getByTestId('coastal-map')).toHaveTextContent('1 markers')
  })

  test('king tide filter keeps only stations at/above threshold', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Bremerton')).toBeInTheDocument())
    // Seattle max high 8.2 >= 8.0 threshold → king; Bremerton 6.2 < 8.0 → hidden
    await userEvent.click(screen.getByRole('button', { name: 'King tide today' }))
    await waitFor(() => expect(screen.queryByText('Bremerton')).not.toBeInTheDocument())
    expect(screen.getByText('Seattle')).toBeInTheDocument()
  })

  test('download link includes radius and radius option', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Seattle')).toBeInTheDocument())
    const link = screen.getByRole('link', { name: /Download \.ics \(50 mi radius\)/ })
    expect(link.getAttribute('href')).toContain('options=hilo,alerts,radius')
    expect(link.getAttribute('href')).toContain('radius_miles=50')
  })

  test('radius slider updates header and download label', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Seattle')).toBeInTheDocument())
    const slider = screen.getByLabelText('Alert radius') as HTMLInputElement
    // fireEvent-style change via userEvent is awkward for range inputs; set directly
    const { fireEvent } = await import('@testing-library/react')
    fireEvent.change(slider, { target: { value: '100' } })
    expect(screen.getByText(/Stations in range · 100 mi radius/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Download \.ics \(100 mi radius\)/ })).toBeInTheDocument()
  })
})
