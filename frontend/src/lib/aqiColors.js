// CPCB AQI categories: one place for colours + band lookups.
// `solid` = chart/gauge fill, `soft` = tinted background, `ink` = readable text on `soft`.
export const CATEGORIES = {
  good:         { key: 'good',         min: 0,   max: 50,  solid: '#2f9e5b', soft: '#e3f4ea', ink: '#14532d' },
  satisfactory: { key: 'satisfactory', min: 51,  max: 100, solid: '#7bb83d', soft: '#eef6dc', ink: '#3b5a0f' },
  moderate:     { key: 'moderate',     min: 101, max: 200, solid: '#f2c230', soft: '#fcf3cf', ink: '#6b4a05' },
  poor:         { key: 'poor',         min: 201, max: 300, solid: '#f08a24', soft: '#fdead3', ink: '#7a3410' },
  very_poor:    { key: 'very_poor',    min: 301, max: 400, solid: '#e0463b', soft: '#fde1de', ink: '#7a1b17' },
  severe:       { key: 'severe',       min: 401, max: 500, solid: '#8b1e3f', soft: '#f5dbe4', ink: '#4a0d20' },
}
export const CATEGORY_ORDER = ['good', 'satisfactory', 'moderate', 'poor', 'very_poor', 'severe']

export function categoryFromAqi(aqi) {
  if (aqi == null || Number.isNaN(aqi)) return 'good'
  const v = Math.round(aqi)
  for (const k of CATEGORY_ORDER) if (v <= CATEGORIES[k].max) return k
  return 'severe'
}

export function colorsFor(category) {
  return CATEGORIES[category] || CATEGORIES.good
}

// Risk level words used by the advice API.
export const RISK_COLORS = {
  Low: CATEGORIES.good,
  Moderate: CATEGORIES.moderate,
  High: CATEGORIES.poor,
  'Very High': CATEGORIES.very_poor,
}
