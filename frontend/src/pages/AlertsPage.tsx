import NavBar from '../components/NavBar'

export default function AlertsPage() {
  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <div className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-textPrimary mb-4">All upcoming events</h1>
        <p className="text-sm text-textSecondary">
          Select a station on the Dashboard to see its upcoming tide events here.
        </p>
      </div>
    </div>
  )
}
