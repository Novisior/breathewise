import { useCallback, useMemo, useState } from 'react'
import { useT } from './i18n/useT.jsx'
import { load, save, validLocation, validProfile } from './lib/storage.js'
import { useAdvice, useAir } from './lib/hooks.js'
import { dropPastHours } from './lib/bestWindow.js'
import LangToggle from './components/LangToggle.jsx'
import Onboarding from './components/Onboarding.jsx'
import Hero, { timeAgo } from './components/Hero.jsx'
import AdviceCard from './components/AdviceCard.jsx'
import BestTimePlanner from './components/BestTimePlanner.jsx'
import ForecastChart from './components/ForecastChart.jsx'
import PollutantGrid from './components/PollutantGrid.jsx'
import WhyItMatters from './components/WhyItMatters.jsx'
import LocationSearch from './components/LocationSearch.jsx'
import { HeroSkeleton, CardSkeleton } from './components/Skeletons.jsx'
import { ErrorPanel, StaleBanner } from './components/ErrorStates.jsx'
import { IconSettings, IconWind, Sheet } from './components/ui.jsx'

function Dashboard({ profile, location, onEditProfile, onChangeLocation }) {
  const { t, lang } = useT()
  const air = useAir(location)
  const advice = useAdvice(profile, air.data, lang)
  const [picking, setPicking] = useState(false)
  const closePicker = useCallback(() => setPicking(false), [])
  // Saved or long-open data may contain hours that are already over: never plan around those.
  const tz = air.data?.location?.timezone
  const forecast = useMemo(() => dropPastHours(air.data?.forecast, tz), [air.data, tz])
  const offline = typeof navigator !== 'undefined' && navigator.onLine === false

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-10 pt-4">
      <header className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-brand-dark"><IconWind /> BreatheWise</div>
        <div className="flex items-center gap-1">
          <LangToggle />
          <button type="button" onClick={onEditProfile} aria-label={t('app.edit_profile')}
                  className="grid h-11 w-11 place-items-center rounded-full text-ink-soft hover:bg-black/5"><IconSettings /></button>
        </div>
      </header>

      {air.status === 'loading' && !air.data && (
        <div className="space-y-4">
          <HeroSkeleton label={t('app.loading')} />
          <CardSkeleton lines={5} label={t('advice.loading')} />
        </div>
      )}

      {air.status === 'error' && !air.data && (
        <div className="space-y-4">
          <ErrorPanel error={air.error} onRetry={air.retry} />
          <button type="button" onClick={() => setPicking(true)} className="min-h-[44px] text-sm font-medium text-brand-dark underline">{t('app.try_other_place')}</button>
        </div>
      )}

      {air.data && (
        <main className="space-y-4">
          {air.status === 'error' && <StaleBanner offline={offline} updatedAt={timeAgo(air.data.updated_at, t)} onRetry={air.reload} />}
          <Hero air={air.data} locationName={location.name} refreshing={air.status === 'refreshing'}
                onRefresh={air.reload} onChangeLocation={() => setPicking(true)} />
          <div className="grid gap-4 md:grid-cols-2 md:items-start">
            <AdviceCard advice={advice} />
            <div className="space-y-4">
              <BestTimePlanner forecast={forecast} />
              <ForecastChart forecast={forecast} />
            </div>
          </div>
          <PollutantGrid pollutants={air.data.pollutants} subIndices={air.data.sub_indices} dominant={air.data.dominant} />
          <WhyItMatters />
        </main>
      )}

      <footer className="mt-8 space-y-1 text-center text-xs leading-relaxed text-ink-faint">
        <p>{t('app.sources')}</p>
        <p>{t('app.not_medical')}</p>
      </footer>

      {picking && (
        <Sheet title={t('app.change_location')} onClose={closePicker} closeLabel={t('common.close')}>
          <LocationSearch autoFocus selected={null} onSelect={(loc) => { setPicking(false); onChangeLocation(loc) }} />
        </Sheet>
      )}
    </div>
  )
}

export default function App() {
  const [profile, setProfile] = useState(() => { const p = load('profile'); return validProfile(p) ? p : null })
  const [location, setLocation] = useState(() => { const l = load('location'); return validLocation(l) ? l : null })
  const [editing, setEditing] = useState(false)

  const done = ({ profile: p, location: l }) => {
    save('profile', p); save('location', l)
    setProfile(p); setLocation(l); setEditing(false)
  }
  const changeLocation = (l) => { save('location', l); setLocation(l) }

  if (!profile || !location || editing) {
    return <Onboarding initial={profile && location ? { profile, location } : undefined} onDone={done} onCancel={() => setEditing(false)} />
  }
  return <Dashboard profile={profile} location={location} onEditProfile={() => setEditing(true)} onChangeLocation={changeLocation} />
}
