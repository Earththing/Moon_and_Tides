import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DownloadButton from '../components/DownloadButton'

describe('DownloadButton', () => {
  it('constructs correct ICS URL from station, year, options', () => {
    render(
      <DownloadButton
        lat={37.7749}
        lon={-122.4194}
        year={2026}
        options={{ hilo: true, alerts: true, slack: false, tidepooling: false, flood: false, perigean: false, radius: false }}
      />
    )
    const link = screen.getByRole('link') as HTMLAnchorElement
    expect(link.href).toContain('/calendar/2026/')
    expect(link.href).toContain('37.7749')
    // jsdom doesn't encode commas in href; check the raw attribute instead
    expect(link.getAttribute('href')).toContain('options=hilo,alerts')
    expect(link.getAttribute('download')).toBeDefined()
  })
})
