import type { TideEvent } from './api'

// Map marker palette (spec: Map screen)
export const MAP_COLORS = {
  high:    '#1b7faa', // at/near high
  rising:  '#5bbfde',
  low:     '#2a9e6a', // at/near low
  falling: '#88cc88',
  king:    '#e8a030', // king tide alert
  unknown: '#a0b0bf',
} as const

export type TidePhase = 'high' | 'rising' | 'low' | 'falling'
export type ColorMode = 'state' | 'range' | 'extremity'

export interface TideStatus {
  heightFt: number | null
  phase: TidePhase | null
  nextEvent: TideEvent | null
  dailyRangeFt: number
  todayMaxHighFt: number | null
  kingTide: boolean
}

const NEAR_EXTREMUM_MIN = 50 // minutes from an H/L event that counts as "at/near"

export function timeToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

/**
 * Compute a station's current tide status from today's hilo events.
 * Height between events is a cosine interpolation (the standard rule-of-twelfths
 * shape); before the first / after the last event we clamp to that event's height.
 * `highThresholdFt` (90th-percentile of yearly highs) marks king-tide days.
 */
export function computeTideStatus(
  hilo: TideEvent[],
  nowMinutes: number,
  highThresholdFt?: number,
): TideStatus {
  if (hilo.length === 0) {
    return { heightFt: null, phase: null, nextEvent: null, dailyRangeFt: 0, todayMaxHighFt: null, kingTide: false }
  }

  const events = [...hilo].sort((a, b) => timeToMinutes(a.time) - timeToMinutes(b.time))
  const heights = events.map(e => e.height_ft)
  const dailyRangeFt = Math.max(...heights) - Math.min(...heights)
  const highs = events.filter(e => e.type === 'H').map(e => e.height_ft)
  const todayMaxHighFt = highs.length ? Math.max(...highs) : null
  const kingTide =
    highThresholdFt !== undefined && todayMaxHighFt !== null && todayMaxHighFt >= highThresholdFt

  const next = events.find(e => timeToMinutes(e.time) > nowMinutes) ?? null
  const prev = [...events].reverse().find(e => timeToMinutes(e.time) <= nowMinutes) ?? null

  // Height estimate
  let heightFt: number
  if (prev && next) {
    const t1 = timeToMinutes(prev.time)
    const t2 = timeToMinutes(next.time)
    const u = (nowMinutes - t1) / (t2 - t1)
    heightFt = prev.height_ft + (next.height_ft - prev.height_ft) * (1 - Math.cos(Math.PI * u)) / 2
  } else {
    heightFt = (prev ?? next)!.height_ft
  }

  // Phase: near an extremum wins; otherwise direction toward the next event
  let phase: TidePhase
  const nearPrev = prev && nowMinutes - timeToMinutes(prev.time) <= NEAR_EXTREMUM_MIN ? prev : null
  const nearNext = next && timeToMinutes(next.time) - nowMinutes <= NEAR_EXTREMUM_MIN ? next : null
  const near = nearPrev ?? nearNext
  if (near) {
    phase = near.type === 'H' ? 'high' : 'low'
  } else if (next) {
    phase = next.type === 'H' ? 'rising' : 'falling'
  } else {
    // After the last event of the day: moving away from it
    phase = prev!.type === 'H' ? 'falling' : 'rising'
  }

  return { heightFt: Math.round(heightFt * 100) / 100, phase, nextEvent: next, dailyRangeFt, todayMaxHighFt, kingTide }
}

/** Marker fill color for 'state' and 'range' modes ('extremity' uses extremityColor). */
export function markerColor(status: TideStatus, mode: 'state' | 'range'): string {
  if (status.phase === null) return MAP_COLORS.unknown

  if (mode === 'state') {
    if (status.kingTide) return MAP_COLORS.king
    return MAP_COLORS[status.phase]
  }

  // range: sequential sky → ocean over 0–15 ft daily swing
  const t = Math.min(status.dailyRangeFt / 15, 1)
  return lerpColor('#5bbfde', '#1b3a5c', t)
}

/** Extremity color needs the threshold explicitly (not all stations have one loaded). */
export function extremityColor(todayMaxHighFt: number | null, highThresholdFt: number | undefined): string {
  if (todayMaxHighFt === null || highThresholdFt === undefined || highThresholdFt <= 0) {
    return MAP_COLORS.unknown
  }
  const ratio = todayMaxHighFt / highThresholdFt
  if (ratio < 0.9) return MAP_COLORS.low       // well below king level
  if (ratio < 1.0) return MAP_COLORS.rising    // approaching
  if (ratio < 1.05) return MAP_COLORS.king     // king tide
  return '#a32d2d'                             // extreme king tide
}

/** Marker radius in px: size = tidal range (today's swing). */
export function markerRadius(dailyRangeFt: number): number {
  return Math.max(5, Math.min(16, 5 + dailyRangeFt * 0.8))
}

function lerpColor(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map(i => parseInt(a.slice(i, i + 2), 16))
  const pb = [1, 3, 5].map(i => parseInt(b.slice(i, i + 2), 16))
  const px = pa.map((v, i) => Math.round(v + (pb[i] - v) * t))
  return '#' + px.map(v => v.toString(16).padStart(2, '0')).join('')
}
