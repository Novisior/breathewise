import { useEffect, useRef, useState } from 'react'
import { geocode, isAbort } from '../lib/api.js'
import { useT } from '../i18n/useT.jsx'
import { IconLocate, IconPin, IconSearch } from './ui.jsx'

const round2 = (n) => Math.round(n * 100) / 100 // ~1 km: matches the API cache, and is kinder to privacy

export default function LocationSearch({ onSelect, autoFocus = false, selected = null }) {
  const { t, lang } = useT()
  const [q, setQ] = useState('')
  const [state, setState] = useState({ status: 'idle', results: [] }) // idle | loading | ok | error
  const [geoMsg, setGeoMsg] = useState(null)
  const [locating, setLocating] = useState(false)
  const ctrl = useRef(null)

  useEffect(() => {
    const text = q.trim()
    ctrl.current?.abort()
    if (text.length < 2) { setState({ status: 'idle', results: [] }); return undefined }
    setState((s) => ({ ...s, status: 'loading' }))
    const c = new AbortController()
    ctrl.current = c
    const timer = setTimeout(() => {
      geocode(text, lang, c.signal)
        .then((r) => setState({ status: 'ok', results: r.results || [] }))
        .catch((e) => { if (!isAbort(e)) setState({ status: 'error', results: [] }) })
    }, 350) // debounce so we don't call the API on every keystroke
    return () => { clearTimeout(timer); c.abort() }
  }, [q, lang])

  // Pick a place: close the dropdown (cancel any in-flight search) and clear the box.
  const pick = (loc) => {
    ctrl.current?.abort()
    setState({ status: 'idle', results: [] })
    setQ('')
    onSelect(loc)
  }

  const useMyLocation = () => {
    setGeoMsg(null)
    if (!('geolocation' in navigator)) { setGeoMsg(t('loc.geo_unsupported')); return }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        pick({ name: t('loc.current'), latitude: round2(pos.coords.latitude), longitude: round2(pos.coords.longitude) })
      },
      (err) => {
        setLocating(false)
        setGeoMsg(err.code === 1 ? t('loc.geo_denied') : t('loc.geo_failed'))
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 10 * 60 * 1000 },
    )
  }

  return (
    <div>
      <button type="button" onClick={useMyLocation} disabled={locating}
              className="flex min-h-[52px] w-full items-center gap-3 rounded-2xl bg-brand px-4 text-left font-semibold text-white shadow-card hover:bg-brand-dark disabled:opacity-70">
        <IconLocate />
        {locating ? t('loc.locating') : t('loc.use_current')}
      </button>
      {geoMsg && <p role="alert" className="mt-2 text-sm text-red-700">{geoMsg}</p>}

      <div className="my-4 flex items-center gap-3 text-xs uppercase tracking-wide text-ink-faint">
        <span className="h-px flex-1 bg-ink/10" />{t('loc.or')}<span className="h-px flex-1 bg-ink/10" />
      </div>

      <label htmlFor="bw-city" className="sr-only">{t('loc.search_label')}</label>
      <div className="relative">
        <IconSearch className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint" />
        <input
          id="bw-city" type="search" value={q} onChange={(e) => setQ(e.target.value)} autoFocus={autoFocus}
          autoComplete="off" placeholder={t('loc.placeholder')} maxLength={80}
          className="min-h-[52px] w-full rounded-2xl border-2 border-transparent bg-white pl-12 pr-4 text-base shadow-card placeholder:text-ink-faint focus:border-brand focus:outline-none"
        />
      </div>

      <div aria-live="polite" className="mt-3">
        {state.status === 'loading' && <p className="px-1 text-sm text-ink-faint">{t('loc.searching')}</p>}
        {state.status === 'error' && <p className="px-1 text-sm text-red-700">{t('loc.search_error')}</p>}
        {state.status === 'ok' && state.results.length === 0 && <p className="px-1 text-sm text-ink-faint">{t('loc.none')}</p>}
        {state.status === 'ok' && state.results.length > 0 && (
          <ul className="overflow-hidden rounded-2xl bg-white shadow-card">
            {state.results.map((r) => (
              <li key={`${r.latitude},${r.longitude},${r.label}`} className="border-b border-ink/5 last:border-0">
                <button type="button"
                        onClick={() => pick({ name: r.label, latitude: round2(r.latitude), longitude: round2(r.longitude) })}
                        className="flex min-h-[52px] w-full items-center gap-3 px-4 py-2 text-left hover:bg-brand-tint">
                  <IconPin className="shrink-0 text-ink-faint" size={18} />
                  <span className="text-[15px]">{r.label}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selected && (
        <p className="mt-3 flex items-center gap-2 rounded-2xl bg-brand-tint px-4 py-3 text-sm text-brand-dark">
          <IconPin size={16} /> {t('loc.selected', { name: selected.name })}
        </p>
      )}
    </div>
  )
}
