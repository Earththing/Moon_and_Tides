import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ReferenceDot, ReferenceArea, ResponsiveContainer,
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
  showDayNight?: boolean
  sunrise?: string | null   // HH:MM local
  sunset?: string | null    // HH:MM local
  monthlyMeanHigh?: (number | null)[]
  monthlyMeanLow?: (number | null)[]
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const TWILIGHT_MINS = 45  // duration of dawn/dusk gradient fade

function nowTimeStr(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function timeToMins(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function snapTo6Min(t: string): string {
  const total = timeToMins(t)
  const snapped = Math.round(total / 6) * 6
  const h = Math.floor(snapped / 60) % 24
  const m = snapped % 60
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`
}

function offsetTime(t: string, deltaMins: number): string {
  const total = Math.max(0, Math.min(1439, timeToMins(t) + deltaMins))
  return snapTo6Min(`${String(Math.floor(total / 60)).padStart(2,'0')}:${String(total % 60).padStart(2,'0')}`)
}

// Custom tooltip for day view (shows 12h time)
function DayTooltip({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ value: number; payload: { time_12h?: string } }>
  label?: string
}) {
  if (!active || !payload?.length || !label) return null
  const h = payload[0].value
  const t12 = payload[0].payload?.time_12h ?? ''
  return (
    <div className="bg-white border border-border rounded shadow-sm px-2 py-1.5 text-xs">
      <div className="font-medium text-textPrimary">{label} {t12 && <span className="text-textSecondary">({t12})</span>}</div>
      <div className="text-oceanLight">{h.toFixed(2)} ft</div>
    </div>
  )
}

// Custom tooltip for week/month hilo view
function HiloTooltip({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ value: number; payload: { type?: string; time_12h?: string } }>
  label?: string
}) {
  if (!active || !payload?.length || !label) return null
  const h = payload[0].value
  const type = payload[0].payload?.type
  const t12 = payload[0].payload?.time_12h ?? ''
  return (
    <div className="bg-white border border-border rounded shadow-sm px-2 py-1.5 text-xs">
      <div className="font-medium text-textPrimary">{label.slice(0, 10)} {t12}</div>
      <div style={{ color: type === 'H' ? tokens.oceanLight : tokens.sea }}>
        {type === 'H' ? 'High' : 'Low'}: {h.toFixed(2)} ft
      </div>
    </div>
  )
}

export default function TideCurveChart({
  curveData, hiloData, floodMinor, view, isToday = false,
  showDayNight = false, sunrise, sunset,
  monthlyMeanHigh, monthlyMeanLow,
}: TideCurveChartProps) {
  const nowSnapped = snapTo6Min(nowTimeStr())
  const canShade = showDayNight && !!sunrise && !!sunset && view === 'day'

  // Pre-compute twilight boundary times for smooth gradient shading
  const preDawn   = canShade ? offsetTime(sunrise!, -TWILIGHT_MINS) : ''
  const sunriseX  = canShade ? snapTo6Min(sunrise!) : ''
  const sunsetX   = canShade ? snapTo6Min(sunset!)  : ''
  const postDusk  = canShade ? offsetTime(sunset!,   TWILIGHT_MINS) : ''

  // ── Year view ─────────────────────────────────────────────────────────────
  if (view === 'year' && monthlyMeanHigh && monthlyMeanLow) {
    const data = MONTHS.map((m, i) => ({
      month: m,
      'Mean High': monthlyMeanHigh[i] != null ? +monthlyMeanHigh[i]!.toFixed(2) : 0,
      'Mean Low':  monthlyMeanLow[i]  != null ? +monthlyMeanLow[i]!.toFixed(2)  : 0,
    }))
    return (
      <div className="w-full h-64 bg-card rounded border border-border p-2">
        <div className="text-xs text-textHint text-center mb-1">Monthly mean high &amp; low — each bar is the average for that month</div>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={tokens.borderLight} />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: tokens.textSecondary }} />
            <YAxis tick={{ fontSize: 11, fill: tokens.textSecondary }} unit=" ft" />
            <Tooltip formatter={(v: unknown) => `${Number(v).toFixed(1)} ft`} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="Mean High" fill={tokens.oceanLight} radius={[2,2,0,0]} />
            <Bar dataKey="Mean Low"  fill={tokens.sea}        radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ── Week / Month view: hilo area chart ────────────────────────────────────
  if (view === 'week' || view === 'month') {
    const dateFmt = (dateStr: string) =>
      new Date(dateStr + 'T12:00:00').toLocaleDateString('en-US', {
        month: 'short', day: 'numeric',
        ...(view === 'week' ? { weekday: 'short' } : {}),
      })

    const chartData = hiloData.map(d => ({
      x: `${d.date} ${d.time}`,
      height_ft: d.height_ft,
      type: d.type,
      time_12h: d.time_12h,
    }))

    // Show one x-axis tick per calendar day
    const seen = new Set<string>()
    const ticks = chartData.filter(d => {
      const key = d.x.slice(0, 10)
      if (seen.has(key)) return false
      seen.add(key); return true
    }).map(d => d.x)

    const viewLabel = view === 'week'
      ? 'High & low tides · one dot per tide, connected to show pattern'
      : 'High & low tides for the month · blue = high, green = low'

    return (
      <div className="w-full h-64 bg-card rounded border border-border p-2">
        <div className="text-xs text-textHint text-center mb-1">{viewLabel}</div>
        <ResponsiveContainer width="100%" height="90%">
          <AreaChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="tideGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={tokens.oceanLight} stopOpacity={0.12} />
                <stop offset="95%" stopColor={tokens.oceanLight} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={tokens.borderLight} />
            <XAxis
              dataKey="x"
              ticks={ticks}
              tickFormatter={v => dateFmt(v.slice(0, 10))}
              tick={{ fontSize: 10, fill: tokens.textSecondary }}
            />
            <YAxis tick={{ fontSize: 10, fill: tokens.textSecondary }} unit=" ft" />
            <Tooltip content={<HiloTooltip />} />
            <Area
              type="monotone"
              dataKey="height_ft"
              stroke={tokens.oceanLight}
              strokeWidth={1.5}
              fill="url(#tideGrad)"
              dot={(props: unknown) => {
                const p = props as { cx: number; cy: number; payload: { type: string } }
                return (
                  <circle
                    key={`${p.cx}-${p.cy}`}
                    cx={p.cx} cy={p.cy} r={3}
                    fill={p.payload.type === 'H' ? tokens.oceanLight : tokens.sea}
                    stroke="white" strokeWidth={1}
                  />
                )
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ── Day view: 6-min area chart ────────────────────────────────────────────
  const chartData = curveData.map(d => ({
    time: d.time,
    time_12h: d.time_12h ?? '',
    height_ft: d.height_ft,
  }))

  const first = chartData[0]?.time ?? '00:00'
  const last  = chartData[chartData.length - 1]?.time ?? '23:54'

  return (
    <div className="w-full h-64 bg-card rounded border border-border p-2">
      {/* Sentinels for tests */}
      {floodMinor !== undefined && <span data-testid="flood-line-sentinel" style={{ display:'none' }} />}
      {isToday              && <span data-testid="now-line-sentinel"   style={{ display:'none' }} />}

      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 24, right: 16, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="tideGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={tokens.oceanLight} stopOpacity={0.20} />
              <stop offset="95%" stopColor={tokens.oceanLight} stopOpacity={0.02} />
            </linearGradient>
            {/* Dawn and dusk gradient blocks — dark→clear and clear→dark */}
            <linearGradient id="dawnGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%"   stopColor="#0a152a" stopOpacity={0.30} />
              <stop offset="100%" stopColor="#0a152a" stopOpacity={0.00} />
            </linearGradient>
            <linearGradient id="duskGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%"   stopColor="#0a152a" stopOpacity={0.00} />
              <stop offset="100%" stopColor="#0a152a" stopOpacity={0.30} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke={tokens.borderLight} />
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: tokens.textSecondary }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10, fill: tokens.textSecondary }} unit=" ft" />
          <Tooltip content={<DayTooltip />} />

          {/* Day/night shading: night blocks + gradient twilight zones */}
          {canShade && (
            <>
              {/* Pre-dawn full night */}
              <ReferenceArea x1={first} x2={preDawn} fill="#0a152a" fillOpacity={0.30} stroke="none" />
              {/* Dawn fade-in */}
              <ReferenceArea x1={preDawn} x2={sunriseX} fill="url(#dawnGrad)" fillOpacity={1} stroke="none" />
              {/* Dusk fade-out */}
              <ReferenceArea x1={sunsetX} x2={postDusk} fill="url(#duskGrad)" fillOpacity={1} stroke="none" />
              {/* Post-dusk full night */}
              <ReferenceArea x1={postDusk} x2={last} fill="#0a152a" fillOpacity={0.30} stroke="none" />
              {/* Sunrise/sunset markers */}
              <ReferenceLine x={sunriseX} stroke="#f59e0b" strokeWidth={1} strokeDasharray="3 4"
                label={{ value: '☀ ' + sunrise, position: 'insideTopLeft', fontSize: 9, fill: '#d97706' }} />
              <ReferenceLine x={sunsetX}  stroke="#6366f1" strokeWidth={1} strokeDasharray="3 4"
                label={{ value: '🌙 ' + sunset, position: 'insideTopRight', fontSize: 9, fill: '#6366f1' }} />
            </>
          )}

          <Area
            type="monotone"
            dataKey="height_ft"
            stroke={tokens.oceanLight}
            strokeWidth={2}
            fill="url(#tideGrad)"
            dot={false}
          />

          {isToday && (
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
