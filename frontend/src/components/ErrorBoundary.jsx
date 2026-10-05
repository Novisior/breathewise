import { Component } from 'react'
import { useT } from '../i18n/useT.jsx'

function Crash() {
  const { t } = useT()
  return (
    <main role="alert" className="mx-auto mt-24 max-w-sm rounded-3xl bg-white p-6 text-center shadow-card">
      <h1 className="text-lg font-semibold">{t('crash.title')}</h1>
      <p className="mt-2 text-sm text-ink-soft">{t('crash.body')}</p>
      <button type="button" onClick={() => window.location.reload()}
              className="mt-5 min-h-[48px] rounded-full bg-brand px-6 font-semibold text-white">{t('crash.reload')}</button>
    </main>
  )
}

/** Last line of defence: a render bug shows a friendly screen instead of a blank page. */
export default class ErrorBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(err) { console.error('UI crashed:', err) }
  render() { return this.state.failed ? <Crash /> : this.props.children }
}
