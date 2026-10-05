import { CATEGORIES, CATEGORY_ORDER } from '../lib/aqiColors.js'
import { useT } from '../i18n/useT.jsx'
import { IconChevron } from './ui.jsx'

export default function WhyItMatters() {
  const { t } = useT()
  return (
    <details className="group rounded-3xl bg-white p-5 shadow-card">
      <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between text-base font-semibold [&::-webkit-details-marker]:hidden">
        {t('why.title')}
        <IconChevron className="transition-transform group-open:rotate-180" />
      </summary>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-ink-soft">
        <p>{t('why.p1')}</p>
        <p>{t('why.p2')}</p>
        <ul className="space-y-1.5" aria-label={t('why.scale')}>
          {CATEGORY_ORDER.map((k) => {
            const c = CATEGORIES[k]
            return (
              <li key={k} className="flex items-center gap-3 rounded-xl px-3 py-2" style={{ background: c.soft, color: c.ink }}>
                <span className="num w-16 shrink-0 text-xs font-bold">{c.min}–{c.max}</span>
                <span><span className="font-semibold">{t(`cat.${k}`)}</span> · {t(`catmeaning.${k}`)}</span>
              </li>
            )
          })}
        </ul>
        <p>{t('why.p3')}</p>
      </div>
    </details>
  )
}
