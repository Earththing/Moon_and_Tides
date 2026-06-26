import NavBar from '../components/NavBar'

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <h1 className="text-2xl font-semibold text-textPrimary">Help</h1>

        <section>
          <h2 className="text-base font-semibold text-textPrimary mb-2">Importing your calendar</h2>
          <ul className="space-y-1 text-sm text-textSecondary list-disc list-inside">
            <li><strong>Google Calendar:</strong> Settings → Import &amp; export → Import</li>
            <li><strong>Apple Calendar:</strong> File → Import, or subscribe to the URL</li>
            <li><strong>Outlook:</strong> File → Open &amp; Export → Import/Export</li>
          </ul>
          <p className="text-sm text-textSecondary mt-2">
            For live updates, use the URL-based subscription (the /calendar/ endpoint) rather than a one-time download.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-textPrimary mb-2">Understanding the data</h2>
          <ul className="space-y-1 text-sm text-textSecondary list-disc list-inside">
            <li>All heights are relative to <strong>MLLW</strong> (Mean Lower Low Water)</li>
            <li>Times are in the station's local time zone (standard or daylight)</li>
            <li>Data comes from the NOAA CO-OPS API — US coastal stations only</li>
            <li>Harmonic stations (marked H) support slack water and tidepooling features</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-textPrimary mb-2">King tides</h2>
          <p className="text-sm text-textSecondary">
            King tides are the highest predicted tides of the year, typically the top 10% of high tides.
            They occur when a new or full moon coincides with the moon's closest approach to Earth (perigee).
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-textPrimary mb-2">Perigean spring tides</h2>
          <p className="text-sm text-textSecondary">
            A Perigean spring tide occurs when the moon is simultaneously at perigee (closest to Earth)
            and at syzygy (new or full moon, aligned with the sun). These produce the largest tidal ranges
            of the year — typically 4–6 times per year.
          </p>
        </section>
      </div>
    </div>
  )
}
