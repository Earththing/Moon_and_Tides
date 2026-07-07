export interface TideEvent {
  date: string
  time: string
  time_12h: string
  height_ft: number
  type: 'H' | 'L'
}

export interface CurvePoint {
  date: string
  time: string
  time_12h: string
  height_ft: number
}

export interface Station {
  id: string
  name: string
  lat: number
  lon: number
  state: string
  tidal: number
  harmonic: number
  station_type?: 'R' | 'S'   // R = reference (harmonic), S = subordinate (corrected hilo only)
  reference_id?: string | null
  distance_miles?: number
  tidal_type?: string
  mean_range_ft?: number | null
  mean_high_ft?: number | null
  mean_low_ft?: number | null
  has_flood_thresholds?: boolean
  flood_minor_ft?: number | null
  flood_moderate_ft?: number | null
}

export interface GeocodeResult {
  lat: number
  lon: number
  display_name: string
}

export interface YearSummary {
  monthly_mean_high: (number | null)[]
  monthly_mean_low: (number | null)[]
  extreme_highs: TideEvent[]
  extreme_lows: TideEvent[]
}

export interface SpecialEvents {
  tidepooling_windows: unknown[]
  slack_water: unknown[]
  perigean_spring_tides: unknown[]
  king_tides: unknown[]
  radius_alerts: unknown[]
  flood_risk: unknown[]
}

export async function geocode(address: string): Promise<GeocodeResult[]> {
  const res = await fetch('/geocode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address }),
  })
  if (!res.ok) throw new Error('Geocode failed')
  return res.json()
}

export async function fetchNearestStations(lat: number, lon: number, count = 5): Promise<Station[]> {
  const res = await fetch(`/api/v1/stations/nearest?lat=${lat}&lon=${lon}&count=${count}`)
  if (!res.ok) throw new Error('Stations fetch failed')
  return res.json()
}

export async function fetchStationsRadius(lat: number, lon: number, radiusMiles: number): Promise<Station[]> {
  const res = await fetch(`/api/v1/stations/radius?lat=${lat}&lon=${lon}&radius_miles=${radiusMiles}`)
  if (!res.ok) throw new Error('Radius stations fetch failed')
  return res.json()
}

export interface MapStationStatus {
  hilo: TideEvent[]
  high_threshold_ft?: number
  low_threshold_ft?: number
  has_flood?: boolean
}

export async function fetchMapStatus(
  ids: string[], date: string, opts: { extremes?: boolean; flood?: boolean } = {}
): Promise<Record<string, MapStationStatus>> {
  const params = new URLSearchParams({ ids: ids.join(','), date })
  if (opts.extremes) params.set('extremes', 'true')
  if (opts.flood) params.set('flood', 'true')
  const res = await fetch(`/api/v1/map/status?${params}`)
  if (!res.ok) throw new Error('Map status fetch failed')
  const data = await res.json()
  return data.stations
}

export async function fetchStation(id: string): Promise<Station> {
  const res = await fetch(`/api/v1/station/${id}`)
  if (!res.ok) throw new Error('Station fetch failed')
  return res.json()
}

export async function fetchTidesDay(stationId: string, date: string): Promise<{ hilo: TideEvent[]; curve: CurvePoint[] }> {
  const res = await fetch(`/api/v1/tides/day?station_id=${stationId}&date=${date}`)
  if (!res.ok) throw new Error('Tides fetch failed')
  return res.json()
}

export async function fetchYearSummary(stationId: string, year: number): Promise<YearSummary> {
  const res = await fetch(`/api/v1/tides/year-summary?station_id=${stationId}&year=${year}`)
  if (!res.ok) throw new Error('Year summary fetch failed')
  return res.json()
}

export async function fetchSpecialEvents(stationId: string, year: number, lat?: number, lon?: number): Promise<SpecialEvents> {
  let url = `/api/v1/special-events?station_id=${stationId}&year=${year}`
  if (lat !== undefined && lon !== undefined) url += `&lat=${lat}&lon=${lon}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Special events fetch failed')
  return res.json()
}

export async function fetchTidesRange(stationId: string, begin: string, end: string): Promise<{ hilo: TideEvent[] }> {
  const res = await fetch(`/api/v1/tides/range?station_id=${stationId}&begin=${begin}&end=${end}`)
  if (!res.ok) throw new Error('Tides range fetch failed')
  return res.json()
}

export interface SolarDay {
  sunrise: string | null      // HH:MM local
  sunset: string | null       // HH:MM local
  sunrise_12h: string | null
  sunset_12h: string | null
  daylight_hours: number
  timezone: string
}

export async function fetchSolarDay(lat: number, lon: number, date: string): Promise<SolarDay> {
  const res = await fetch(`/api/v1/solar-day?lat=${lat}&lon=${lon}&date=${date}`)
  if (!res.ok) throw new Error('Solar day fetch failed')
  return res.json()
}

export async function fetchSolarRange(
  lat: number, lon: number, begin: string, end: string
): Promise<(SolarDay & { date: string })[]> {
  const res = await fetch(`/api/v1/solar-range?lat=${lat}&lon=${lon}&begin=${begin}&end=${end}`)
  if (!res.ok) throw new Error('Solar range fetch failed')
  return res.json()
}

export function icsUrl(lat: number, lon: number, year: number, options = 'hilo,alerts', radiusMiles?: number): string {
  let url = `/calendar/${year}/${lat},${lon}.ics?options=${options}`
  if (radiusMiles !== undefined) url += `&radius_miles=${radiusMiles}`
  return url
}
