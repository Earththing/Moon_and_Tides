import { Link, useLocation } from 'react-router-dom'

export default function NavBar() {
  const { pathname } = useLocation()
  const link = (to: string, label: string) => (
    <Link
      to={to}
      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
        pathname === to
          ? 'bg-white/20 text-white'
          : 'text-white/75 hover:text-white hover:bg-white/10'
      }`}
    >
      {label}
    </Link>
  )
  return (
    <nav className="bg-ocean text-white px-4 py-3 flex items-center gap-6 shadow">
      <Link to="/" className="font-semibold text-white text-lg tracking-tight">
        Moon &amp; Tides
      </Link>
      <div className="flex gap-1">
        {link('/', 'Dashboard')}
        {link('/map', 'Map')}
        {link('/alerts', 'Alerts')}
        {link('/help', 'Help')}
      </div>
    </nav>
  )
}
