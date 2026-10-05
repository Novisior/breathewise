import { RISK_COLORS } from '../lib/aqiColors.js'
import { useT } from '../i18n/useT.jsx'
import { Card, IconCheck, IconClock, IconMask, IconX } from './ui.jsx'
import { CardSkeleton } from './Skeletons.jsx'
import { ErrorPanel } from './ErrorStates.jsx'

const RISK_KEY = { Low: 'low', Moderate: 'moderate', High: 'high', 'Very High': 'very_high' }
// Only mention a fallback when something actually went wrong (not when AI simply isn't set up).
const SHOW_FALLBACK = new Set(['ai_error', 'ai_cooldown', 'ai_invalid_output', 'ai_rejected_by_safety'])

export default function AdviceCard({ advice }) {
  const { t } = useT()
  if (advice.status === 'loading' || advice.status === 'idle') return <CardSkeleton lines={6} label={t('advice.loading')} />
  if (advice.status === 'error') return <ErrorPanel error={advice.error} onRetry={advice.retry} titleKey="advice.error_title" />

  const a = advice.data
  const risk = RISK_COLORS[a.risk_level] || RISK_COLORS.Moderate
  const isAi = a.source === 'ai'

  return (
    <Card aria-labelledby="advice-title" aria-busy={advice.upgrading}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="advice-title" className="text-base font-semibold tracking-tight">{t('advice.title')}</h2>
        <span className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide" style={{ background: risk.soft, color: risk.ink }}>
          {t('advice.risk', { level: t(`risk.${RISK_KEY[a.risk_level] || 'moderate'}`) })}
        </span>
      </div>

      <p className="text-[17px] leading-snug">{a.summary}</p>

      <div className="mt-4 flex items-center gap-3 rounded-2xl bg-paper px-4 py-3">
        <IconMask className="shrink-0 text-ink-soft" size={24} />
        <p className="text-sm font-medium">{t(`mask.${a.mask}`)}</p>
      </div>

      {a.do?.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-1.5 text-sm font-semibold text-brand-dark">{t('advice.do')}</h3>
          <ul className="space-y-2">
            {a.do.map((x, i) => (
              <li key={i} className="flex gap-2.5 text-[15px] leading-snug">
                <IconCheck size={18} className="mt-0.5 shrink-0 text-brand" strokeWidth={3} /><span>{x}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {a.avoid?.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-1.5 text-sm font-semibold text-red-800">{t('advice.avoid')}</h3>
          <ul className="space-y-2">
            {a.avoid.map((x, i) => (
              <li key={i} className="flex gap-2.5 text-[15px] leading-snug">
                <IconX size={18} className="mt-0.5 shrink-0 text-red-600" strokeWidth={3} /><span>{x}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 space-y-3 border-t border-ink/10 pt-4 text-sm">
        <div>
          <h3 className="font-semibold">{t('advice.exercise')}</h3>
          <p className="mt-0.5 text-ink-soft">{a.exercise_advice}</p>
        </div>
        <div>
          <h3 className="flex items-center gap-1.5 font-semibold"><IconClock size={16} />{t('advice.timing')}</h3>
          <p className="mt-0.5 text-ink-soft">{a.best_time_window}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
        <span className={`rounded-full px-2.5 py-1 font-semibold ${isAi ? 'bg-brand-tint text-brand-dark' : 'bg-ink/5 text-ink-soft'}`}>
          {isAi ? t('advice.src_ai') : t('advice.src_rules')}
        </span>
        {advice.saved && <span>{t('advice.saved')}</span>}
        {advice.upgrading && <span role="status" className="animate-pulse">{t('advice.upgrading')}</span>}
        {!isAi && !advice.upgrading && SHOW_FALLBACK.has(a.fallback_reason) && <span>{t('advice.fallback')}</span>}
      </div>

      {/* Fixed text added by the server, always shown. */}
      <p className="mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-900">{a.disclaimer}</p>
    </Card>
  )
}
