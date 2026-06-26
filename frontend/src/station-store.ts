const KEY_STATION = 'tideline_station'
const KEY_YEAR    = 'tideline_year'

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
