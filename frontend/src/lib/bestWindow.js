// Best-time planner: pure functions, no timezone maths.
// Forecast times are *local to the location* ("2026-10-01T14:00"), so we never build a
// browser-local Date from them; we only split the string and do arithmetic on the parts.
import { categoryFromAqi } from './aqiColors.js'

export function parseLocal(t) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(t || '')
  if (!m) return null
  const [, y, mo, d, h] = m
  // Absolute hour counter (UTC used purely as a calendar calculator).
  const absHour = Date.UTC(+y, +mo - 1, +d, +h) / 3_600_000
  return { date: `${y}-${mo}-${d}`, hour: +h, absHour }
}

export function formatHour(h) {
  const hh = ((h % 24) + 24) % 24
  const suffix = hh < 12 ? 'AM' : 'PM'
  const twelve = hh % 12 === 0 ? 12 : hh % 12
  return `${twelve} ${suffix}`
}

export const pointAqi = (p) => (p.aqi_instant ?? p.aqi)

/**
 * Find the best (lowest mean AQI) or worst consecutive window of `hours` slots.
 * Only daytime slots count (default 6 AM to 9 PM) because that is when people go out.
 * Returns null when there is not enough usable data.
 */
function findWindow(forecast, { hours = 2, horizon = 24, dayStart = 6, dayEnd = 21 } = {}, mode) {
  const pts = (forecast || []).slice(0, horizon).map((p) => ({ p, t: parseLocal(p.time) }))
  if (!pts.length || pts.some((x) => !x.t)) return null
  const baseDate = pts[0].t.date
  let best = null
  for (let i = 0; i + hours <= pts.length; i++) {
    const slice = pts.slice(i, i + hours)
    const consecutive = slice.every((x, k) => k === 0 || x.t.absHour - slice[k - 1].t.absHour === 1)
    const daytime = slice.every((x) => x.t.hour >= dayStart && x.t.hour < dayEnd)
    if (!consecutive || !daytime) continue
    const avg = slice.reduce((s, x) => s + pointAqi(x.p), 0) / hours
    const better = !best || (mode === 'best' ? avg < best.avg : avg > best.avg) // ties keep the earliest
    if (better) best = { index: i, avg, slice }
  }
  if (!best) return null
  const first = best.slice[0].t
  const last = best.slice[best.slice.length - 1].t
  const dayOffset = Math.round((Date.parse(first.date) - Date.parse(baseDate)) / 86_400_000)
  const avg = Math.round(best.avg)
  return {
    index: best.index,
    hours,
    avg,
    category: categoryFromAqi(avg),
    startHour: first.hour,
    endHour: (last.hour + 1) % 24,
    startLabel: formatHour(first.hour),
    endLabel: formatHour(last.hour + 1),
    dayOffset, // 0 = same local date as the first forecast point, 1 = next day
    includesNow: best.index === 0,
  }
}

export const findBestWindow = (forecast, opts) => findWindow(forecast, opts, 'best')
export const findWorstWindow = (forecast, opts) => findWindow(forecast, opts, 'worst')

/** Next `n` hours for the planner strip, flagging which slots belong to the best window. */
export function hourlyStrip(forecast, best, n = 24) {
  return (forecast || []).slice(0, n).map((p, i) => {
    const t = parseLocal(p.time)
    const aqi = pointAqi(p)
    return {
      time: p.time,
      hour: t ? t.hour : 0,
      aqi,
      category: categoryFromAqi(aqi),
      inBest: !!best && i >= best.index && i < best.index + best.hours,
    }
  })
}

/** "YYYY-MM-DDTHH" for the current hour in an IANA timezone (null if unavailable). */
export function localHourString(timeZone, nowMs = Date.now()) {
  try {
    const s = new Intl.DateTimeFormat('sv-SE', {
      timeZone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).format(new Date(nowMs)) // "2026-10-03 05:13"
    return s.replace(' ', 'T').slice(0, 13)
  } catch {
    return null
  }
}

/**
 * Remove forecast hours that are already over, so saved (offline) data or a tab left open
 * for hours never recommends a window in the past. Falls back to the input if timezone is unknown.
 */
export function dropPastHours(forecast, timeZone, nowMs = Date.now()) {
  const now = timeZone ? localHourString(timeZone, nowMs) : null
  if (!now || !Array.isArray(forecast)) return forecast || []
  return forecast.filter((p) => typeof p.time === 'string' && p.time.slice(0, 13) >= now)
}
