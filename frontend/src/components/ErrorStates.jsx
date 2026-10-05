import { useT } from '../i18n/useT.jsx'
import { Card } from './ui.jsx'

/** kind: 'network' | 'timeout' | 'server' | 'client' (from ApiError). */
export function ErrorPanel({ error, onRetry, titleKey = 'err.title' }) {
  const { t } = useT()
  const kind = error?.kind || 'server'
  const body = { network: 'err.network', timeout: 'err.timeout', server: 'err.server', client: 'err.client' }[kind] || 'err.server'
  return (
    <Card role="alert" className="border border-red-100">
      <h2 className="text-base font-semibold">{t(titleKey)}</h2>
      <p className="mt-1 text-sm text-ink-soft">{t(body)}</p>
      {kind === 'server' && error?.message && <p className="mt-1 text-xs text-ink-faint">{error.message}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry}
                className="mt-4 min-h-[44px] rounded-full bg-brand px-5 text-sm font-semibold text-white hover:bg-brand-dark">
          {t('err.retry')}
        </button>
      )}
    </Card>
  )
}

export function StaleBanner({ updatedAt, onRetry, offline = false }) {
  const { t } = useT()
  return (
    <div role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <span>{t(offline ? 'err.offline' : 'err.stale', { time: updatedAt })}</span>
      <button type="button" onClick={onRetry} className="min-h-[36px] rounded-full px-3 font-semibold underline">{t('err.retry')}</button>
    </div>
  )
}
