import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import en from './en.json'
import hi from './hi.json'
import { load, save } from '../lib/storage.js'

const DICTS = { en, hi }
export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
]

const Ctx = createContext({ lang: 'en', setLang: () => {}, t: (k) => k })

function initialLang() {
  const saved = load('lang', null)
  if (DICTS[saved]) return saved
  // First visit: follow the browser language if it is Hindi.
  try { if ((navigator.language || '').toLowerCase().startsWith('hi')) return 'hi' } catch { /* ignore */ }
  return 'en'
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(initialLang)
  const setLang = useCallback((l) => { if (DICTS[l]) { setLangState(l); save('lang', l) } }, [])
  useEffect(() => { try { document.documentElement.lang = lang } catch { /* ignore */ } }, [lang])
  const t = useCallback((key, vars) => {
    let s = DICTS[lang]?.[key] ?? DICTS.en[key] ?? key
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v))
    return s
  }, [lang])
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useT = () => useContext(Ctx)
