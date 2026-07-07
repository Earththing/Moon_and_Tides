const KEY_STATION = 'tideline_station'
const KEY_YEAR    = 'tideline_year'
const KEY_LAT     = 'tideline_lat'
const KEY_LON     = 'tideline_lon'
const KEY_LOC     = 'tideline_location'

export function saveLocation(lat: number, lon: number, name: string) {
  localStorage.setItem(KEY_LAT, String(lat))
  localStorage.setItem(KEY_LON, String(lon))
  localStorage.setItem(KEY_LOC, name)
}

export function loadLocation(): { lat: number; lon: number; name: string } | null {
  const lat = localStorage.getItem(KEY_LAT)
  const lon = localStorage.getItem(KEY_LON)
  if (!lat || !lon) return null
  return { lat: Number(lat), lon: Number(lon), name: localStorage.getItem(KEY_LOC) ?? '' }
}

export function saveStation(id: string, year: number) {
  localStorage.setItem(KEY_STATION, id)
  localStorage.setItem(KEY_YEAR, String(year))
}

export function loadStation(): { id: string; year: number } | null {
  const id = localStorage.getItem(KEY_STATION)
  const year = localStorage.getItem(KEY_YEAR)
  if (!id) return null
  return { id, year: year ? Number(year) : new Date().getFullYear() }
}

export function alertsUrl(): string {
  const saved = loadStation()
  if (!saved) return '/alerts'
  return `/alerts?station=${saved.id}&year=${saved.year}`
}
