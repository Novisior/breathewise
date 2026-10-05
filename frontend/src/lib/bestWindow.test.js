import test from 'node:test'
import assert from 'node:assert/strict'
import { findBestWindow, findWorstWindow, formatHour, hourlyStrip, parseLocal } from './bestWindow.js'
import { categoryFromAqi } from './aqiColors.js'

// Build hourly points starting at a local date/hour with a value function.
function series(startDate, startHour, count, fn) {
  const out = []
  for (let i = 0; i < count; i++) {
    const abs = Date.UTC(+startDate.slice(0, 4), +startDate.slice(5, 7) - 1, +startDate.slice(8, 10), startHour + i)
    const d = new Date(abs).toISOString().slice(0, 13) + ':00'
    out.push({ time: d, aqi: fn(i, new Date(abs).getUTCHours()), aqi_instant: null })
  }
  return out
}

test('formatHour', () => {
  assert.equal(formatHour(0), '12 AM')
  assert.equal(formatHour(12), '12 PM')
  assert.equal(formatHour(15), '3 PM')
  assert.equal(formatHour(24), '12 AM')
})

test('parseLocal rejects garbage and parses parts', () => {
  assert.equal(parseLocal('nope'), null)
  assert.deepEqual({ ...parseLocal('2026-10-01T14:00') }.hour, 14)
})

test('categoryFromAqi uses CPCB bands', () => {
  assert.equal(categoryFromAqi(50), 'good')
  assert.equal(categoryFromAqi(51), 'satisfactory')
  assert.equal(categoryFromAqi(200), 'moderate')
  assert.equal(categoryFromAqi(201), 'poor')
  assert.equal(categoryFromAqi(400), 'very_poor')
  assert.equal(categoryFromAqi(401), 'severe')
  assert.equal(categoryFromAqi(900), 'severe')
})

test('best window picks the cleanest daytime pair', () => {
  // from 8 AM: dirty morning, clean 1-3 PM
  const f = series('2026-10-01', 8, 24, (i, h) => (h === 13 || h === 14 ? 60 : 180))
  const w = findBestWindow(f, { hours: 2 })
  assert.equal(w.startLabel, '1 PM')
  assert.equal(w.endLabel, '3 PM')
  assert.equal(w.avg, 60)
  assert.equal(w.category, 'satisfactory')
  assert.equal(w.dayOffset, 0)
  assert.equal(w.includesNow, false)
})

test('night-time lows are ignored', () => {
  // 3 AM is the cleanest hour of all, but nobody should be told to go out at 3 AM
  const f = series('2026-10-01', 20, 24, (i, h) => (h >= 1 && h <= 4 ? 10 : 150))
  const w = findBestWindow(f, { hours: 2 })
  assert.ok(w.startHour >= 6 && w.endHour <= 21 + 0, `got ${w.startLabel}`)
  assert.equal(w.avg, 150)
})

test('window on the next day is flagged with dayOffset 1', () => {
  const f = series('2026-10-01', 20, 24, (i, h) => (h === 7 || h === 8 ? 40 : 160))
  const w = findBestWindow(f, { hours: 2 })
  assert.equal(w.startLabel, '7 AM')
  assert.equal(w.dayOffset, 1)
})

test('prefers instant AQI when present and keeps earliest on ties', () => {
  const f = series('2026-10-01', 8, 6, () => 100)
  f.forEach((p) => { p.aqi_instant = 100 })
  assert.equal(findBestWindow(f, { hours: 2 }).startLabel, '8 AM')
  f[3].aqi_instant = 20 // hour 11
  f[3].aqi = 300
  assert.equal(findBestWindow(f, { hours: 1 }).startLabel, '11 AM')
})

test('gaps in the forecast do not form a window', () => {
  const f = series('2026-10-01', 8, 6, () => 100)
  f.splice(2, 1) // remove 10 AM -> 9 AM and 11 AM are not adjacent
  const w = findBestWindow(f.slice(1, 3), { hours: 2 }) // [9AM, 11AM]
  assert.equal(w, null)
})

test('returns null for empty / too-short / unparseable data', () => {
  assert.equal(findBestWindow([], {}), null)
  assert.equal(findBestWindow(series('2026-10-01', 8, 1, () => 50), { hours: 2 }), null)
  assert.equal(findBestWindow([{ time: 'bad', aqi: 1 }], { hours: 1 }), null)
  assert.equal(findBestWindow(undefined), null)
})

test('worst window and strip flags', () => {
  const f = series('2026-10-01', 8, 24, (i, h) => (h === 18 ? 320 : 100))
  const worst = findWorstWindow(f, { hours: 2 })
  assert.ok(worst.avg >= 210)
  const best = findBestWindow(f, { hours: 2 })
  const strip = hourlyStrip(f, best, 24)
  assert.equal(strip.length, 24)
  assert.equal(strip.filter((s) => s.inBest).length, 2)
})

import { dropPastHours, localHourString } from './bestWindow.js'

test('localHourString converts to the location timezone', () => {
  // 2026-10-02T23:43:00Z is 05:13 next day in India (UTC+5:30)
  const now = Date.UTC(2026, 9, 2, 23, 43)
  assert.equal(localHourString('Asia/Kolkata', now), '2026-10-03T05')
  assert.equal(localHourString('Not/AZone', now), null)
})

test('dropPastHours removes finished hours, keeps current hour onwards', () => {
  const f = series('2026-10-03', 0, 12, () => 100) // 00:00 .. 11:00
  const now = Date.UTC(2026, 9, 2, 23, 43) // 05:13 in Kolkata
  const kept = dropPastHours(f, 'Asia/Kolkata', now)
  assert.equal(kept[0].time, '2026-10-03T05:00')
  assert.equal(kept.length, 7)
  assert.equal(dropPastHours(f, undefined, now).length, 12) // unknown tz: untouched
  assert.deepEqual(dropPastHours(undefined, 'Asia/Kolkata', now), [])
})
