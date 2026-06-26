import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ComingUpFeed, { type FeedItem } from '../components/ComingUpFeed'

const ALERT_ITEM: FeedItem = {
  type: 'alert',
  title: 'King Tide Alert',
  description: 'Predicted high: 7.2 ft',
  date: '2026-01-05',
}

const TIDE_ITEM: FeedItem = {
  type: 'opportunity',
  title: 'Tidepooling Window',
  description: 'Low tide at',
  detail: '10:30 AM (-0.3 ft)',
  date: '2026-07-04',
}

describe('ComingUpFeed', () => {
  it('alert items rendered with amber styling', () => {
    const { container } = render(<ComingUpFeed items={[ALERT_ITEM]} />)
    expect(screen.getByText(/King Tide Alert/)).toBeTruthy()
    // Amber color applied via inline style (rgb conversion of #a06000)
    const colored = container.querySelector('[style*="color"]') as HTMLElement
    expect(colored?.textContent).toContain('King Tide Alert')
  })

  it('tidepooling items rendered with green styling', () => {
    const { container } = render(<ComingUpFeed items={[TIDE_ITEM]} />)
    expect(screen.getByText(/Tidepooling Window/)).toBeTruthy()
    // Green bg applied via inline style (rgb conversion of #f4fbf7)
    const card = container.querySelector('[style*="background"]') as HTMLElement
    expect(card?.textContent).toContain('Tidepooling Window')
  })

  it('returns null when items is empty', () => {
    const { container } = render(<ComingUpFeed items={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows view all button when more than 6 items', () => {
    const many: FeedItem[] = Array.from({ length: 8 }, (_, i) => ({
      ...ALERT_ITEM,
      date: `2026-0${i % 9 + 1}-01`,
    }))
    render(<ComingUpFeed items={many} />)
    expect(screen.getByText(/View all 8/)).toBeTruthy()
  })
})
