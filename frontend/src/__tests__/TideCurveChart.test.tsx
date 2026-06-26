import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import TideCurveChart from '../components/TideCurveChart'
import type { CurvePoint, TideEvent } from '../api'

function makeCurve(n: number): CurvePoint[] {
  return Array.from({ length: n }, (_, i) => ({
    date: '2026-06-21',
    time: `${String(Math.floor(i * 6 / 60)).padStart(2,'0')}:${String((i * 6) % 60).padStart(2,'0')}`,
    time_12h: '12:00 PM',
    height_ft: 3 + 2 * Math.sin(i / 10),
  }))
}

function makeHilo(): TideEvent[] {
  return [
    { date: '2026-06-21', time: '06:00', time_12h: '6:00 AM', height_ft: 5.5, type: 'H' },
    { date: '2026-06-21', time: '12:00', time_12h: '12:00 PM', height_ft: 0.8, type: 'L' },
    { date: '2026-06-21', time: '18:00', time_12h: '6:00 PM', height_ft: 5.0, type: 'H' },
  ]
}

describe('TideCurveChart', () => {
  it('day view renders without error with 240 data points', () => {
    const { container } = render(
      <TideCurveChart curveData={makeCurve(240)} hiloData={makeHilo()} view="day" stationId="9414290" />
    )
    expect(container.firstChild).toBeTruthy()
  })

  it('flood ReferenceLine absent when floodMinor prop not provided', () => {
    const { container } = render(
      <TideCurveChart curveData={makeCurve(240)} hiloData={makeHilo()} view="day" stationId="9414290" />
    )
    expect(container.querySelector('[data-testid="flood-line-sentinel"]')).toBeNull()
  })

  it('flood ReferenceLine present when floodMinor prop provided', () => {
    const { container } = render(
      <TideCurveChart curveData={makeCurve(240)} hiloData={makeHilo()} view="day" stationId="9414290" floodMinor={4.5} />
    )
    expect(container.querySelector('[data-testid="flood-line-sentinel"]')).toBeTruthy()
  })

  it('now ReferenceLine sentinel absent when isToday is false', () => {
    const { container } = render(
      <TideCurveChart curveData={makeCurve(240)} hiloData={makeHilo()} view="day" stationId="9414290" isToday={false} />
    )
    expect(container.querySelector('[data-testid="now-line-sentinel"]')).toBeNull()
  })

  it('now ReferenceLine sentinel present when isToday is true', () => {
    const { container } = render(
      <TideCurveChart curveData={makeCurve(240)} hiloData={makeHilo()} view="day" stationId="9414290" isToday={true} />
    )
    expect(container.querySelector('[data-testid="now-line-sentinel"]')).toBeTruthy()
  })

  it('year view renders bar chart', () => {
    const { container } = render(
      <TideCurveChart
        curveData={[]}
        hiloData={[]}
        view="year"
        stationId="9414290"
        monthlyMeanHigh={Array(12).fill(5.5)}
        monthlyMeanLow={Array(12).fill(0.8)}
      />
    )
    expect(container.firstChild).toBeTruthy()
  })
})
