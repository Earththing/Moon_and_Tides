import { icsUrl } from '../api'

interface Props {
  lat: number
  lon: number
  year: number
  options: Record<string, boolean>
}

export default function DownloadButton({ lat, lon, year, options }: Props) {
  const optStr = Object.entries(options)
    .filter(([, v]) => v)
    .map(([k]) => k)
    .join(',')

  const href = icsUrl(lat, lon, year, optStr || 'hilo')

  return (
    <a
      href={href}
      download
      className="block w-full text-center py-2 px-4 bg-oceanLight text-white text-sm font-semibold rounded hover:bg-ocean transition-colors"
    >
      Download .ics ({year})
    </a>
  )
}
