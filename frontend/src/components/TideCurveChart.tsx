import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ReferenceDot, ResponsiveContainer,
  BarChart, Bar, Legend,
} from 'recharts'
import { tokens } from '../tokens'
import type { TideEvent, CurvePoint } from '../api'

export interface TideCurveChartProps {
  curveData: CurvePoint[]
  hiloData: TideEvent[]
  floodMinor?: number
  view: 'day' | 'week' | 'month' | 'year'
  stationId: string
  isToday?: boolean
  monthlyMeanHigh?: (number | null)[]
  monthlyMeanLow?: (number | null)[]
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function nowTimeStr(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

// Snap HH:MM to the nearest 6-minute boundary so it matches a curve data point.
// Curve data arrives in 6-min intervals: 00:00, 00:06, 00:12 …
function snapTo6Min(timeStr: string): string {
  const [h, m] = timeStr.split(':').map(Number)
  const snapped = Math.round((h * 60 + m) / 6) * 6
  const sh = Math.floor(snapped / 60) % 24
  const sm = snapped % 60
  return `${String(sh).padStart(2, '0')}:${String(sm).padStart(2, '0')}`
}

export default function TideCurveChart({
  curveData, hiloData, floodMinor, view, isToday = false,
  monthlyMeanHigh, monthlyMeanLow,
}: TideCurveChartProps) {
  const nowSnapped = snapTo6Min(nowTimeStr())

  if (view === 'year' && monthlyMeanHigh && monthlyMeanLow) {
    const data = MONTHS.map((m, i) => ({
      month: m,
      high: monthlyMeanHigh[i] ?? 0,
      low: monthlyMeanLow[i] ?? 0,
    }))
    return (
      <div className="w-full h-64 bg-card rounded border border-border p-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 24, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={tokens.borderLight} />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: tokens.textSecondary }} />
            <YAxis tick={{ fontSize: 11, fill: tokens.textSecondary }} unit=" ft" />
            <Tooltip formatter={(v: unknown) => `${Number(v).toFixed(1)} ft`} />
            <Legend />
            <Bar dataKey="high" name="Mean High" fill={tokens.oceanLight} radius={[2,2,0,0]} />
            <Bar dataKey="low" name="Mean Low" fill={tokens.sea} radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  const chartData = view === 'month'
    ? hiloData.map(d => ({ time: `${d.date} ${d.time}`, height_ft: d.height_ft, type: d.type }))
    : curveData.map(d => ({ time: d.time, height_ft: d.height_ft }))

  return (
    <div className="w-full h-64 bg-card rounded border border-border p-2">
      {/* Sentinel for tests — Recharts SVG doesn't render in jsdom */}
      {floodMinor !== undefined && (
        <span data-testid="flood-line-sentinel" style={{ display: 'none' }} />
      )}
      {isToday && (
        <span data-testid="now-line-sentinel" style={{ display: 'none' }} />
      )}
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 24, right: 12, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="tideGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={tokens.oceanLight} stopOpacity={0.20} />
              <stop offset="95%" stopColor={tokens.oceanLight} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={tokens.borderLight} />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: tokens.textSecondary }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 10, fill: tokens.textSecondary }} unit=" ft" />
          <Tooltip formatter={(v: unknown) => [`${Number(v).toFixed(2)} ft`, 'Height']} />
          <Area
            type="monotone"
            dataKey="height_ft"
            stroke={tokens.oceanLight}
            strokeWidth={2}
            fill="url(#tideGrad)"
            dot={false}
          />

          {/* "Now" line — only on today's view, snapped to nearest 6-min data point */}
          {isToday && view === 'day' && (
            <ReferenceLine
              x={nowSnapped}
              stroke={tokens.sky}
              strokeWidth={2}
              strokeDasharray="4 3"
              label={{ value: 'now', position: 'insideTopRight', fontSize: 10, fill: tokens.sky }}
            />
          )}

          {floodMinor !== undefined && (
            <ReferenceLine
              y={floodMinor}
              stroke={tokens.danger}
              strokeDasharray="4 3"
              label={{ value: 'flood', position: 'insideTopRight', fontSize: 10, fill: tokens.danger }}
              ifOverflow="extendDomain"
            />
          )}

          {hiloData.map((d, i) => (
            <ReferenceDot
              key={i}
              x={d.time}
              y={d.height_ft}
              r={4}
              fill={d.type === 'H' ? tokens.oceanLight : tokens.sea}
              stroke="white"
              strokeWidth={1}
              label={{
                value: `${d.height_ft.toFixed(1)}`,
                position: d.type === 'H' ? 'top' : 'bottom',
                fontSize: 9,
                fill: tokens.textSecondary,
              }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
