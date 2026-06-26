import NavBar from '../components/NavBar'

export default function MapPage() {
  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <div className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-textPrimary mb-4">Station map</h1>
        <p className="text-sm text-textSecondary">Map view coming in a future update.</p>
      </div>
    </div>
  )
}
