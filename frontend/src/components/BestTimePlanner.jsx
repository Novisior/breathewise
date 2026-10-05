import { colorsFor } from '../lib/aqiColors.js'
import { findBestWindow, findWorstWindow, formatHour, hourlyStrip } from '../lib/bestWindow.js'
import { useT } from '../i18n/useT.jsx'
import { Card, CardTitle } from './ui.jsx'

const BAD = new Set(['poor', 'very_poor', 'severe'])

export default function BestTimePlanner({ forecast }) {
  const { t } = useT()
  const best = findBestWindow(forecast, { hours: 2, horizon: 24 })
  const worst = findWorstWindow(forecast, { hours: 2, horizon: 24 })
  const strip = hourlyStrip(forecast, best, 24)

  if (!best || strip.length === 0) {
    return (
      <Card aria-labelledby="planner-title">
        <h2 id="planner-title" className="mb-1 text-base font-semibold tracking-tight">{t('planner.title')}</h2>
        <p className="text-sm text-ink-soft">{t('planner.no_data')}</p>
      </Card>
    )
  }

  const c = colorsFor(best.category)
  const day = best.includesNow ? t('planner.now') : best.dayOffset === 0 ? t('planner.today') : t('planner.tomorrow')
  const allBad = BAD.has(best.category)
  const worstBad = worst && BAD.has(worst.category) && worst.index !== best.index

  return (
    <Card aria-labelledby="planner-title">
      <h2 id="planner-title" className="sr-only">{t('planner.title')}</h2>
      <CardTitle hint={t('planner.hint')}>{t('planner.title')}</CardTitle>

      <div className="rounded-2xl px-4 py-3" style={{ background: c.soft, color: c.ink }}>
        <p className="text-xs font-semibold uppercase tracking-wide opacity-80">{day}</p>
        <p className="num text-2xl font-bold">{best.startLabel} – {best.endLabel}</p>
        <p className="text-sm">{t('planner.avg', { aqi: best.avg, label: t(`cat.${best.category}`) })}</p>
      </div>

      {allBad && <p role="alert" className="mt-3 text-sm text-red-800">{t('planner.all_bad')}</p>}
      {worstBad && (
        <p className="mt-3 text-sm text-ink-soft">
          {t('planner.avoid', { from: worst.startLabel, to: worst.endLabel, day: worst.dayOffset === 0 ? t('planner.today') : t('planner.tomorrow') })}
        </p>
      )}

      <div className="mt-4" role="img"
           aria-label={t('planner.strip_label', { from: best.startLabel, to: best.endLabel })}>
        <div className="flex h-14 items-end gap-[3px]">
          {strip.map((s) => (
            <div key={s.time} title={`${formatHour(s.hour)}: AQI ${s.aqi}`}
                 className={`flex-1 rounded-t-md ${s.inBest ? 'ring-2 ring-ink ring-offset-1' : ''}`}
                 style={{ background: colorsFor(s.category).solid, height: `${Math.max(14, Math.min(100, (s.aqi / 400) * 100))}%` }} />
          ))}
        </div>
        <div className="num mt-1 flex justify-between text-[11px] text-ink-faint">
          <span>{formatHour(strip[0].hour)}</span>
          <span>{formatHour(strip[Math.floor(strip.length / 2)].hour)}</span>
          <span>{formatHour(strip[strip.length - 1].hour)}</span>
        </div>
      </div>
    </Card>
  )
}
