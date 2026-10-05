import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { categoryFromAqi, colorsFor } from '../lib/aqiColors.js'
import { formatHour, parseLocal, pointAqi } from '../lib/bestWindow.js'
import { useT } from '../i18n/useT.jsx'
import { Card, CardTitle } from './ui.jsx'

function ChartTooltip({ active, payload }) {
  const { t } = useT()
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  const c = colorsFor(p.category)
  return (
    <div className="rounded-xl bg-white px-3 py-2 text-sm shadow-card">
      <p className="font-semibold">{p.dayLabel} {formatHour(p.hour)}</p>
      <p className="num" style={{ color: c.ink }}>AQI {p.aqi} · {t(`cat.${p.category}`)}</p>
    </div>
  )
}

export default function ForecastChart({ forecast }) {
  const { t } = useT()
  const pts = (forecast || []).slice(0, 48)
  const firstDate = pts[0] ? parseLocal(pts[0].time)?.date : null
  const data = pts.map((p) => {
    const lt = parseLocal(p.time)
    const aqi = pointAqi(p)
    return { time: p.time, hour: lt?.hour ?? 0, aqi, category: categoryFromAqi(aqi), dayLabel: lt?.date === firstDate ? t('planner.today') : t('chart.later') }
  })

  if (data.length < 2) return null

  const ticks = data.filter((d) => d.hour % 6 === 0).map((d) => d.time)
  const midnights = data.filter((d, i) => d.hour === 0 && i > 0).map((d) => d.time)
  const peak = data.reduce((m, d) => (d.aqi > m.aqi ? d : m), data[0])

  return (
    <Card aria-labelledby="chart-title">
      <h2 id="chart-title" className="sr-only">{t('chart.title')}</h2>
      <CardTitle hint={t('chart.hint')}>{t('chart.title')}</CardTitle>
      <div role="img" aria-label={t('chart.summary', { hours: data.length, peak: peak.aqi, time: formatHour(peak.hour) })} className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: -18, bottom: 0 }} barCategoryGap={1}>
            <XAxis dataKey="time" ticks={ticks} tickFormatter={(v) => formatHour(parseLocal(v)?.hour ?? 0)}
                   tick={{ fontSize: 11, fill: '#7a8987' }} axisLine={false} tickLine={false} interval={0} />
            <YAxis tick={{ fontSize: 11, fill: '#7a8987' }} axisLine={false} tickLine={false} width={42}
                   domain={[0, (max) => Math.max(100, Math.ceil(max / 50) * 50)]} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(0,0,0,.05)' }} />
            {midnights.map((m) => <ReferenceLine key={m} x={m} stroke="#7a8987" strokeDasharray="3 3" />)}
            <Bar dataKey="aqi" radius={[3, 3, 0, 0]} isAnimationActive={false}>
              {data.map((d) => <Cell key={d.time} fill={colorsFor(d.category).solid} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
