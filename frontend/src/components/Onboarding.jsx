import { useState } from 'react'
import { useT } from '../i18n/useT.jsx'
import LocationSearch from './LocationSearch.jsx'
import LangToggle from './LangToggle.jsx'
import { Chip, IconWind } from './ui.jsx'

const AGES = ['child', 'teen', 'adult', 'senior']
const CONDITIONS = ['asthma', 'copd', 'heart_disease', 'diabetes', 'pregnancy']
const ROUTINES = ['outdoor_exercise', 'commute_two_wheeler', 'commute_walk', 'commute_public_transport', 'commute_car', 'outdoor_work', 'mostly_indoors']
const STEPS = 4

const toggle = (arr, v) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v])

/** 4 short steps: age, health, routine, location. Also used to edit the profile later. */
export default function Onboarding({ initial, onDone, onCancel }) {
  const { t } = useT()
  const editing = !!initial?.profile
  const [step, setStep] = useState(0)
  const [age, setAge] = useState(initial?.profile?.age_group || null)
  const [conds, setConds] = useState(initial?.profile?.conditions || [])
  const [routine, setRoutine] = useState(initial?.profile?.routine || [])
  const [location, setLocation] = useState(initial?.location || null)

  const canPregnancy = age === 'teen' || age === 'adult'
  const visibleConds = CONDITIONS.filter((c) => c !== 'pregnancy' || canPregnancy)
  const canNext = step === 0 ? !!age : step === 3 ? !!location : true

  const finish = () => {
    onDone({
      profile: {
        age_group: age,
        conditions: conds.filter((c) => c !== 'pregnancy' || canPregnancy),
        routine,
      },
      location,
    })
  }
  const next = () => (step === STEPS - 1 ? finish() : setStep(step + 1))

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col px-4 pb-6 pt-6">
      <header className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-brand-dark"><IconWind /> BreatheWise</div>
        <div className="flex items-center gap-2">
          <LangToggle />
          {editing && <button type="button" onClick={onCancel} className="min-h-[44px] px-2 text-sm font-medium text-ink-soft underline">{t('common.cancel')}</button>}
        </div>
      </header>

      <div className="mb-6" role="progressbar" aria-valuemin={1} aria-valuemax={STEPS} aria-valuenow={step + 1}
           aria-label={t('onb.progress', { n: step + 1, total: STEPS })}>
        <div className="flex gap-1.5">
          {Array.from({ length: STEPS }).map((_, i) => (
            <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? 'bg-brand' : 'bg-ink/10'}`} />
          ))}
        </div>
        <p className="mt-2 text-xs text-ink-faint">{t('onb.progress', { n: step + 1, total: STEPS })}</p>
      </div>

      <div className="flex-1">
        {step === 0 && (
          <fieldset>
            {!editing && <p className="mb-5 rounded-2xl bg-brand-tint px-4 py-3 text-sm text-brand-dark">{t('onb.welcome')}</p>}
            <legend className="mb-1 text-2xl font-semibold tracking-tight">{t('onb.age_title')}</legend>
            <p className="mb-4 text-sm text-ink-soft">{t('onb.age_sub')}</p>
            <div className="space-y-2.5" role="radiogroup" aria-label={t('onb.age_title')}>
              {AGES.map((a) => (
                <Chip key={a} role="radio" selected={age === a} onClick={() => setAge(a)} sub={t(`age.${a}.sub`)}>{t(`age.${a}`)}</Chip>
              ))}
            </div>
          </fieldset>
        )}

        {step === 1 && (
          <fieldset>
            <legend className="mb-1 text-2xl font-semibold tracking-tight">{t('onb.cond_title')}</legend>
            <p className="mb-4 text-sm text-ink-soft">{t('onb.cond_sub')}</p>
            <div className="space-y-2.5">
              {visibleConds.map((c) => (
                <Chip key={c} selected={conds.includes(c)} onClick={() => setConds(toggle(conds, c))}>{t(`cond.${c}`)}</Chip>
              ))}
              <Chip selected={conds.length === 0} onClick={() => setConds([])}>{t('cond.none')}</Chip>
            </div>
            <p className="mt-4 text-xs text-ink-faint">{t('onb.privacy')}</p>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset>
            <legend className="mb-1 text-2xl font-semibold tracking-tight">{t('onb.routine_title')}</legend>
            <p className="mb-4 text-sm text-ink-soft">{t('onb.routine_sub')}</p>
            <div className="space-y-2.5">
              {ROUTINES.map((r) => (
                <Chip key={r} selected={routine.includes(r)} onClick={() => setRoutine(toggle(routine, r))}>{t(`routine.${r}`)}</Chip>
              ))}
            </div>
          </fieldset>
        )}

        {step === 3 && (
          <div>
            <h1 className="mb-1 text-2xl font-semibold tracking-tight">{t('onb.loc_title')}</h1>
            <p className="mb-4 text-sm text-ink-soft">{t('onb.loc_sub')}</p>
            <LocationSearch selected={location} onSelect={setLocation} />
          </div>
        )}
      </div>

      <div className="sticky bottom-0 -mx-4 mt-6 flex gap-3 bg-paper/95 px-4 pb-2 pt-3 backdrop-blur">
        {step > 0 && (
          <button type="button" onClick={() => setStep(step - 1)}
                  className="min-h-[52px] rounded-2xl bg-white px-5 font-semibold text-ink shadow-card">{t('common.back')}</button>
        )}
        <button type="button" onClick={next} disabled={!canNext}
                className="min-h-[52px] flex-1 rounded-2xl bg-brand px-5 font-semibold text-white shadow-card hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-40">
          {step === STEPS - 1 ? (editing ? t('common.save') : t('onb.finish')) : t('common.next')}
        </button>
      </div>
    </main>
  )
}
