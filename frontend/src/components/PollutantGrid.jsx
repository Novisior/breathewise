import { categoryFromAqi, colorsFor } from '../lib/aqiColors.js'
import { useT } from '../i18n/useT.jsx'
import { Card, CardTitle } from './ui.jsx'

const ITEMS = [
  { key: 'pm2_5', name: 'PM2.5', unit: 'µg/m³' },
  { key: 'pm10', name: 'PM10', unit: 'µg/m³' },
  { key: 'no2', name: 'NO₂', unit: 'µg/m³' },
  { key: 'o3', name: 'O₃', unit: 'µg/m³' },
  { key: 'so2', name: 'SO₂', unit: 'µg/m³' },
  { key: 'co', name: 'CO', unit: 'mg/m³' },
]

export default function PollutantGrid({ pollutants, subIndices, dominant }) {
  const { t } = useT()
  return (
    <Card aria-labelledby="poll-title">
      <h2 id="poll-title" className="sr-only">{t('poll.title')}</h2>
      <CardTitle hint={t('poll.hint')}>{t('poll.title')}</CardTitle>
      <ul className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        {ITEMS.map(({ key, name, unit }) => {
          const value = pollutants?.[key]
          const sub = subIndices?.[key]
          const c = colorsFor(sub != null ? categoryFromAqi(sub) : 'good')
          const isDom = key === dominant
          return (
            <li key={key} className={`rounded-2xl p-3 ${isDom ? 'ring-2 ring-ink/70' : ''}`} style={{ background: sub != null ? c.soft : '#f6f4ee', color: sub != null ? c.ink : '#4b5b59' }}>
              <div className="flex items-center justify-between text-xs font-semibold">
                <span>{name}</span>
                {isDom && <span className="rounded-full bg-white/80 px-1.5 py-0.5 text-[10px] uppercase">{t('poll.main')}</span>}
              </div>
              <p className="num mt-1 text-xl font-bold">{value != null ? value : '—'}<span className="ml-1 text-[11px] font-medium opacity-70">{value != null ? unit : ''}</span></p>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/70" aria-hidden="true">
                <div className="h-full rounded-full" style={{ width: `${sub != null ? Math.max(4, Math.min(100, (sub / 400) * 100)) : 0}%`, background: c.solid }} />
              </div>
              <p className="num mt-1 text-[11px] opacity-80">{sub != null ? t('poll.sub', { n: sub }) : t('poll.na')}</p>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
