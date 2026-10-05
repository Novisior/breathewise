import { colorsFor, categoryFromAqi } from '../lib/aqiColors.js'
import { useT } from '../i18n/useT.jsx'
import { IconInfo, IconPin, IconRefresh } from './ui.jsx'

const POLLUTANT_NAMES = { pm2_5: 'PM2.5', pm10: 'PM10', no2: 'NO₂', o3: 'O₃', so2: 'SO₂', co: 'CO' }
export const pollutantName = (k) => POLLUTANT_NAMES[k] || k

export function timeAgo(iso, t) {
  const ms = Date.now() - Date.parse(iso)
  if (!Number.isFinite(ms) || ms < 0) return t('time.just_now')
  const min = Math.round(ms / 60000)
  if (min < 1) return t('time.just_now')
  if (min < 60) return t('time.min_ago', { n: min })
  const h = Math.round(min / 60)
  return t('time.hour_ago', { n: h })
}

function Gauge({ aqi, color }) {
  const R = 84
  const C = 2 * Math.PI * R
  const frac = Math.max(0.04, Math.min(aqi, 500) / 500)
  return (
    <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90" aria-hidden="true">
      <circle cx="100" cy="100" r={R} fill="none" stroke="rgba(0,0,0,.08)" strokeWidth="14" />
      <circle cx="100" cy="100" r={R} fill="none" stroke={color} strokeWidth="14" strokeLinecap="round"
              strokeDasharray={`${C * frac} ${C}`} />
    </svg>
  )
}

export default function Hero({ air, locationName, onChangeLocation, onRefresh, refreshing }) {
  const { t } = useT()
  const cat = colorsFor(air.category)
  const label = t(`cat.${air.category}`)
  const instantDiffers = air.aqi_instant != null && Math.abs(air.aqi_instant - air.aqi) >= 15
  const { temperature_c: temp, humidity_pct: hum } = air.weather || {}

  return (
    <section aria-labelledby="hero-title" className="rounded-3xl p-5 shadow-card"
             style={{ background: `linear-gradient(160deg, ${cat.soft} 0%, #ffffff 90%)`, color: cat.ink }}>
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onChangeLocation}
                className="flex min-h-[44px] min-w-0 items-center gap-1.5 rounded-full bg-white/70 px-3 text-sm font-semibold"
                aria-label={t('hero.change_location', { name: locationName })}>
          <IconPin size={16} /><span className="truncate">{locationName}</span>
        </button>
        <button type="button" onClick={onRefresh} disabled={refreshing} aria-label={t('hero.refresh')}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-white/70 disabled:opacity-60">
          <IconRefresh className={refreshing ? 'animate-spin' : ''} />
        </button>
      </div>

      <h1 id="hero-title" className="sr-only">{t('hero.sr_title', { aqi: air.aqi, label })}</h1>
      <div className="relative mx-auto my-4 h-52 w-52">
        <Gauge aqi={air.aqi} color={cat.solid} />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="num text-6xl font-bold leading-none">{air.aqi}</span>
          <span className="mt-1 text-xs font-semibold uppercase tracking-widest opacity-70">{t('hero.aqi')}</span>
        </div>
      </div>

      <p className="text-center text-2xl font-semibold">{label}</p>
      {instantDiffers && (
        <p className="mt-1 text-center text-sm opacity-80">
          {t('hero.right_now', { aqi: air.aqi_instant, label: t(`cat.${air.category_instant || categoryFromAqi(air.aqi_instant)}`) })}
        </p>
      )}
      <p className="mt-1 text-center text-sm opacity-80">{t('hero.main_pollutant', { name: pollutantName(air.dominant) })}</p>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-sm">
        {temp != null && <span className="num rounded-full bg-white/70 px-3 py-1">{Math.round(temp)}°C</span>}
        {hum != null && <span className="num rounded-full bg-white/70 px-3 py-1">{t('hero.humidity', { n: Math.round(hum) })}</span>}
        <span className="rounded-full bg-white/70 px-3 py-1">{t('hero.updated', { time: timeAgo(air.updated_at, t) })}</span>
      </div>

      {air.approximate && (
        <p className="mt-3 flex items-start gap-2 rounded-2xl bg-white/70 px-3 py-2 text-xs">
          <IconInfo size={16} className="mt-0.5 shrink-0" />{t('hero.approx')}
        </p>
      )}
    </section>
  )
}
