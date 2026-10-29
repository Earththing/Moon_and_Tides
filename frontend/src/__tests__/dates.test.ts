import { describe, it, expect, vi, afterEach } from 'vitest'
import { localDateStr, todayStr } from '../dates'

describe('dates', () => {
  afterEach(() => { vi.useRealTimers() })

  it('localDateStr uses local fields, not UTC', () => {
    // Local 2026-10-28 23:30 is 2026-10-29 in UTC for any zone west of UTC;
    // the local date must win either way.
    expect(localDateStr(new Date(2026, 9, 28, 23, 30))).toBe('2026-10-28')
    expect(localDateStr(new Date(2027, 0, 1, 0, 5))).toBe('2027-01-01')
  })

  it('todayStr matches the local calendar date', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 11, 31, 22, 0))
    expect(todayStr()).toBe('2026-12-31')
  })
})
