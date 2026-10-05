import { LANGUAGES, useT } from '../i18n/useT.jsx'

export default function LangToggle() {
  const { lang, setLang, t } = useT()
  return (
    <div role="group" aria-label={t('lang.label')} className="inline-flex rounded-full bg-white p-0.5 text-sm shadow-card">
      {LANGUAGES.map((l) => (
        <button key={l.code} type="button" onClick={() => setLang(l.code)} aria-pressed={lang === l.code} lang={l.code}
                className={`min-h-[40px] rounded-full px-3 font-medium ${lang === l.code ? 'bg-brand text-white' : 'text-ink-soft'}`}>
          {l.label}
        </button>
      ))}
    </div>
  )
}
