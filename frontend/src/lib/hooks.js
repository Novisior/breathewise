import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchAdvice, fetchAir, isAbort } from './api.js'
import { load, save } from './storage.js'

const REFRESH_AFTER_MS = 15 * 60 * 1000 // matches the server's air cache TTL

/**
 * Loads air data for a location. Keeps the last good response in localStorage so the app
 * still shows something (with a banner) when offline or when the server is down.
 * status: loading | ok | refreshing | error  (error + data = showing saved/old data)
 */
export function useAir(location) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null })
  const ctrl = useRef(null)
  const loadedAt = useRef(0)
  const lat = location?.latitude
  const lon = location?.longitude

  const load_ = useCallback((keepOld = false) => {
    if (lat == null || lon == null) return
    ctrl.current?.abort()
    const c = new AbortController()
    ctrl.current = c
    setState((s) => ({ status: keepOld && s.data ? 'refreshing' : 'loading', data: keepOld ? s.data : null, error: null }))
    fetchAir(lat, lon, c.signal)
      .then((data) => {
        loadedAt.current = Date.now()
        save('snapshot', { lat, lon, data })
        setState({ status: 'ok', data, error: null })
      })
      .catch((error) => {
        if (isAbort(error)) return
        setState((s) => {
          if (s.data) return { status: 'error', data: s.data, error } // keep what is on screen
          const snap = load('snapshot')
          if (snap && snap.lat === lat && snap.lon === lon && snap.data) return { status: 'error', data: snap.data, error }
          return { status: 'error', data: null, error }
        })
      })
  }, [lat, lon])

  useEffect(() => {
    load_(false)
    return () => ctrl.current?.abort()
  }, [load_])

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === 'visible' && Date.now() - loadedAt.current > REFRESH_AFTER_MS) load_(true)
    }
    const onOnline = () => load_(true) // connection is back: refresh automatically
    document.addEventListener('visibilitychange', onVis)
    window.addEventListener('online', onOnline)
    return () => {
      document.removeEventListener('visibilitychange', onVis)
      window.removeEventListener('online', onOnline)
    }
  }, [load_])

  return { ...state, reload: () => load_(true), retry: () => load_(false) }
}

/**
 * Two-step advice: instant rules-based answer first (use_ai=false), then ask again with
 * use_ai=true to upgrade it. If the upgrade fails, the first answer simply stays.
 * If everything fails, the last advice saved for the same profile/language/place is shown.
 */
export function useAdvice(profile, air, language) {
  const [state, setState] = useState({ status: 'idle', data: null, error: null, upgrading: false, saved: false })
  const [tick, setTick] = useState(0)
  const airKey = air ? `${air.location?.latitude},${air.location?.longitude},${air.updated_at}` : null
  const airRef = useRef(air)
  airRef.current = air
  const profileKey = JSON.stringify(profile)

  useEffect(() => {
    const a = airRef.current
    if (!a || !profile) return undefined
    const c = new AbortController()
    const storeKey = `${profileKey}|${language}|${a.location?.latitude},${a.location?.longitude}`
    setState({ status: 'loading', data: null, error: null, upgrading: false, saved: false })
    ;(async () => {
      try {
        const first = await fetchAdvice({ profile, language, air: a, useAi: false }, c.signal)
        save('advice', { key: storeKey, data: first })
        setState({ status: 'ok', data: first, error: null, upgrading: first.source !== 'ai', saved: false })
        if (first.source === 'ai') return // already have cached AI advice
        const upgraded = await fetchAdvice({ profile, language, air: a, useAi: true }, c.signal)
        save('advice', { key: storeKey, data: upgraded })
        setState({ status: 'ok', data: upgraded, error: null, upgrading: false, saved: false })
      } catch (error) {
        if (isAbort(error)) return
        setState((s) => {
          if (s.data) return { ...s, upgrading: false }
          const snap = load('advice')
          if (snap && snap.key === storeKey && snap.data) return { status: 'ok', data: snap.data, error: null, upgrading: false, saved: true }
          return { status: 'error', data: null, error, upgrading: false, saved: false }
        })
      }
    })()
    return () => c.abort()
    // profileKey stands in for `profile` so a new-but-equal object doesn't refetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [airKey, profileKey, language, tick])

  return { ...state, retry: () => setTick((n) => n + 1) }
}
