import { describe, expect, test } from 'vitest'
import type { TideEvent } from '../api'
import {
  computeTideStatus, markerColor, extremityColor, markerRadius,
  timeToMinutes, MAP_COLORS,
} from '../tide-status'

const HILO: TideEvent[] = [
  { date: '2026-06-21', time: '03:15', time_12h: '3:15 AM', height_ft: 5.2, type: 'H' },
  { date: '2026-06-21', time: '09:30', time_12h: '9:30 AM', height_ft: 0.8, type: 'L' },
  { date: '2026-06-21', time: '15:45', time_12h: '3:45 PM', height_ft: 4.9, type: 'H' },
  { date: '2026-06-21', time: '21:00', time_12h: '9:00 PM', height_ft: 1.1, type: 'L' },
]

describe('computeTideStatus', () => {
  test('empty hilo yields null status', () => {
    const s = computeTideStatus([], 600)
    expect(s.phase).toBeNull()
    expect(s.heightFt).toBeNull()
  })

  test('rising between low and high', () => {
    // 12:30 — between 09:30 L and 15:45 H, not near either
    const s = computeTideStatus(HILO, timeToMinutes('12:30'))
    expect(s.phase).toBe('rising')
    expect(s.nextEvent?.type).toBe('H')
    // Interpolated height must sit between the two extremes
    expect(s.heightFt!).toBeGreaterThan(0.8)
    expect(s.heightFt!).toBeLessThan(4.9)
  })

  test('falling between high and low', () => {
    const s = computeTideStatus(HILO, timeToMinutes('18:30'))
    expect(s.phase).toBe('falling')
    expect(s.nextEvent?.type).toBe('L')
  })

  test('at/near high within 50 minutes of an H event', () => {
    expect(computeTideStatus(HILO, timeToMinutes('15:30')).phase).toBe('high') // 15 min before
    expect(computeTideStatus(HILO, timeToMinutes('16:15')).phase).toBe('high') // 30 min after
  })

  test('at/near low within 50 minutes of an L event', () => {
    expect(computeTideStatus(HILO, timeToMinutes('09:10')).phase).toBe('low')
  })

  test('height at an extremum matches the event height', () => {
    const s = computeTideStatus(HILO, timeToMinutes('09:30'))
    expect(s.heightFt).toBeCloseTo(0.8, 5)
  })

  test('daily range is max minus min', () => {
    const s = computeTideStatus(HILO, 600)
    expect(s.dailyRangeFt).toBeCloseTo(5.2 - 0.8, 5)
  })

  test('after last event of day: falling away from a low means rising', () => {
    const s = computeTideStatus(HILO, timeToMinutes('22:30'))
    expect(s.phase).toBe('rising') // last event was L at 21:00, >50 min ago
    expect(s.nextEvent).toBeNull()
  })

  test('king tide flagged when max high meets threshold', () => {
    expect(computeTideStatus(HILO, 600, 5.0).kingTide).toBe(true)
    expect(computeTideStatus(HILO, 600, 6.0).kingTide).toBe(false)
    expect(computeTideStatus(HILO, 600).kingTide).toBe(false) // no threshold
  })
})

describe('markerColor', () => {
  test('state mode maps phases to spec colors', () => {
    expect(markerColor(computeTideStatus(HILO, timeToMinutes('12:30')), 'state')).toBe(MAP_COLORS.rising)
    expect(markerColor(computeTideStatus(HILO, timeToMinutes('15:45')), 'state')).toBe(MAP_COLORS.high)
    expect(markerColor(computeTideStatus(HILO, timeToMinutes('09:30')), 'state')).toBe(MAP_COLORS.low)
    expect(markerColor(computeTideStatus(HILO, timeToMinutes('18:30')), 'state')).toBe(MAP_COLORS.falling)
  })

  test('king tide overrides phase color in state mode', () => {
    const s = computeTideStatus(HILO, timeToMinutes('12:30'), 5.0)
    expect(markerColor(s, 'state')).toBe(MAP_COLORS.king)
  })

  test('range mode: larger range is darker', () => {
    const small = markerColor(computeTideStatus(HILO, 600), 'range')
    const big = markerColor(
      computeTideStatus(HILO.map(e => ({ ...e, height_ft: e.height_ft * 3 })), 600),
      'range',
    )
    expect(small).not.toBe(big)
  })
})

describe('extremityColor', () => {
  test('unknown without a threshold', () => {
    expect(extremityColor(5.2, undefined)).toBe(MAP_COLORS.unknown)
    expect(extremityColor(null, 6.0)).toBe(MAP_COLORS.unknown)
  })

  test('graded colors by ratio to king threshold', () => {
    expect(extremityColor(4.0, 6.0)).toBe(MAP_COLORS.low)     // 0.67
    expect(extremityColor(5.8, 6.0)).toBe(MAP_COLORS.rising)  // 0.97
    expect(extremityColor(6.1, 6.0)).toBe(MAP_COLORS.king)    // 1.02
    expect(extremityColor(7.0, 6.0)).toBe('#a32d2d')          // 1.17
  })
})

describe('markerRadius', () => {
  test('clamped between 5 and 16 px', () => {
    expect(markerRadius(0)).toBe(5)
    expect(markerRadius(50)).toBe(16)
    expect(markerRadius(5)).toBeCloseTo(9, 5)
  })
})
