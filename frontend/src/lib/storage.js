// localStorage wrapper that never throws (private mode / blocked storage / corrupt JSON).
const PREFIX = 'bw.'

export function load(key, fallback = null) {
  try {
    const raw = window.localStorage.getItem(PREFIX + key)
    return raw == null ? fallback : JSON.parse(raw)
  } catch {
    return fallback
  }
}

export function save(key, value) {
  try {
    window.localStorage.setItem(PREFIX + key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

export function remove(key) {
  try { window.localStorage.removeItem(PREFIX + key) } catch { /* ignore */ }
}

// Shape checks so a stale or hand-edited value can't crash the app.
const AGES = ['child', 'teen', 'adult', 'senior']
export function validProfile(p) {
  return !!p && AGES.includes(p.age_group) && Array.isArray(p.conditions) && Array.isArray(p.routine)
}
export function validLocation(l) {
  return !!l && typeof l.name === 'string' && Number.isFinite(l.latitude) && Number.isFinite(l.longitude)
}
