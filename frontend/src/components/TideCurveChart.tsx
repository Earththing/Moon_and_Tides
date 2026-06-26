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
  monthlyMeanHigh?: (number | null)[]
  monthlyMeanLow?: (number | null)[]
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function nowTimeStr(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

export default function TideCurveChart({
  curveData, hiloData, floodMinor, view,
  monthlyMeanHigh, monthlyMeanLow,
}: TideCurveChartProps) {
  const nowStr = nowTimeStr()

  if (view === 'year' && monthlyMeanHigh && monthlyMeanLow) {
    const data = MONTHS.map((m, i) => ({
      month: m,
      high: monthlyMeanHigh[i] ?? 0,
      low: monthlyMeanLow[i] ?? 0,
    }))
    return (
      <div className="w-full h-48 bg-card rounded border border-border p-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
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

  const xKey = 'time'

  return (
    <div className="w-full h-48 bg-card rounded border border-border p-2">
      {/* Sentinel div for flood line — Recharts SVG content doesn't render in jsdom */}
      {floodMinor !== undefined && (
        <span data-testid="flood-line-sentinel" style={{ display: 'none' }} />
      )}
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="tideGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={tokens.oceanLight} stopOpacity={0.20} />
              <stop offset="95%" stopColor={tokens.oceanLight} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={tokens.borderLight} />
          <XAxis
            dataKey={xKey}
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
          {view === 'day' && (
            <ReferenceLine
              x={nowStr}
              stroke={tokens.sky}
              strokeDasharray="4 3"
              label={{ value: 'now', position: 'top', fontSize: 10, fill: tokens.sky }}
            />
          )}
          {floodMinor !== undefined && (
            <ReferenceLine
              y={floodMinor}
              stroke={tokens.danger}
              strokeDasharray="4 3"
              label={{ value: 'flood', position: 'right', fontSize: 10, fill: tokens.danger }}
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
              label={{ value: `${d.height_ft.toFixed(1)}`, position: 'top', fontSize: 9, fill: tokens.textSecondary }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
