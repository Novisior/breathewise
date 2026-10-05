// Thin client for the BreatheWise backend. Every call has a timeout and returns
// typed errors so the UI can tell "you're offline" from "our server had a problem".
const BASE = (import.meta.env?.VITE_API_BASE || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(kind, message, status) {
    super(message)
    this.kind = kind // 'network' | 'timeout' | 'server' | 'client'
    this.status = status
  }
}

function detailText(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg // FastAPI 422
  return null
}

async function request(path, { method = 'GET', body, signal, timeoutMs = 15000 } = {}) {
  const ctrl = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => { timedOut = true; ctrl.abort() }, timeoutMs)
  const onAbort = () => ctrl.abort()
  if (signal) {
    if (signal.aborted) ctrl.abort()
    else signal.addEventListener('abort', onAbort, { once: true })
  }
  try {
    const res = await fetch(BASE + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
    if (!res.ok) {
      let msg = null
      try { msg = detailText((await res.json()).detail) } catch { /* not JSON */ }
      throw new ApiError(res.status >= 500 ? 'server' : 'client', msg || `Request failed (${res.status})`, res.status)
    }
    return await res.json()
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e?.name === 'AbortError') {
      if (timedOut) throw new ApiError('timeout', 'The server took too long to respond.')
      throw e // caller cancelled on purpose: let it be ignored
    }
    throw new ApiError('network', 'Could not reach the server.')
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
}

export const isAbort = (e) => e?.name === 'AbortError'

export const fetchAir = (lat, lon, signal) =>
  request(`/api/air?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`, { signal })

export const geocode = (q, lang, signal) =>
  request(`/api/geocode?q=${encodeURIComponent(q)}&lang=${lang}`, { signal, timeoutMs: 8000 })

// Send only what /api/advice needs (the server ignores extras, but smaller is faster).
function adviceAir(air) {
  return {
    aqi: air.aqi,
    category: air.category,
    dominant: air.dominant,
    aqi_instant: air.aqi_instant,
    category_instant: air.category_instant,
    pollutants: air.pollutants,
    forecast: (air.forecast || []).slice(0, 48).map((p) => ({
      time: p.time, aqi: p.aqi, category: p.category, dominant: p.dominant,
      aqi_instant: p.aqi_instant, category_instant: p.category_instant, pm2_5: p.pm2_5,
    })),
  }
}

export const fetchAdvice = ({ profile, language, air, useAi }, signal) =>
  request('/api/advice', {
    method: 'POST',
    signal,
    timeoutMs: useAi ? 30000 : 10000, // backend gives the AI ~20 s before falling back
    body: { profile, language, air: adviceAir(air), use_ai: useAi },
  })
