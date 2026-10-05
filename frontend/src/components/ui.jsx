import { useEffect, useRef } from 'react'

const I = ({ children, size = 20, className = '', ...p }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className} {...p}>{children}</svg>
)
export const IconCheck = (p) => <I {...p}><path d="M20 6 9 17l-5-5" /></I>
export const IconX = (p) => <I {...p}><path d="M18 6 6 18M6 6l12 12" /></I>
export const IconPin = (p) => <I {...p}><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></I>
export const IconRefresh = (p) => <I {...p}><path d="M21 12a9 9 0 1 1-3-6.7L21 8" /><path d="M21 3v5h-5" /></I>
export const IconSettings = (p) => <I {...p}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" /></I>
export const IconMask = (p) => <I {...p}><path d="M4 9c0-1 .7-2 2-2h12c1.3 0 2 1 2 2v3c0 3-3.5 6-8 6s-8-3-8-6V9Z" /><path d="M2 10h2M20 10h2M8 13h8" /></I>
export const IconClock = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></I>
export const IconInfo = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></I>
export const IconSearch = (p) => <I {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></I>
export const IconLocate = (p) => <I {...p}><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /><circle cx="12" cy="12" r="8" /></I>
export const IconWind = (p) => <I {...p}><path d="M3 8h10a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h7a2 2 0 1 1-2 2" /></I>
export const IconChevron = (p) => <I {...p}><path d="m6 9 6 6 6-6" /></I>

export function Card({ children, className = '', as: Tag = 'section', ...rest }) {
  return <Tag className={`rounded-3xl bg-white p-5 shadow-card ${className}`} {...rest}>{children}</Tag>
}

export function CardTitle({ children, hint }) {
  return (
    <div className="mb-3">
      <h2 className="text-base font-semibold tracking-tight text-ink">{children}</h2>
      {hint && <p className="mt-0.5 text-xs text-ink-faint">{hint}</p>}
    </div>
  )
}

/** Big tappable choice. Always 48px+ tall so it works one-handed on a phone. */
export function Chip({ selected, onClick, children, sub, role }) {
  return (
    <button
      type="button"
      role={role}
      aria-pressed={role ? undefined : selected}
      aria-checked={role ? selected : undefined}
      onClick={onClick}
      className={`flex min-h-[52px] w-full items-center justify-between gap-3 rounded-2xl border-2 px-4 py-3 text-left transition-colors ${
        selected ? 'border-brand bg-brand-tint text-brand-dark' : 'border-transparent bg-white text-ink shadow-card hover:border-brand/30'
      }`}
    >
      <span>
        <span className="block text-[15px] font-medium leading-snug">{children}</span>
        {sub && <span className="block text-xs text-ink-faint">{sub}</span>}
      </span>
      <span aria-hidden="true" className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 ${selected ? 'border-brand bg-brand text-white' : 'border-ink-faint/40'}`}>
        {selected && <IconCheck size={14} strokeWidth={3} />}
      </span>
    </button>
  )
}

/** Bottom sheet on phones, centred dialog on larger screens. Esc / backdrop closes it. */
export function Sheet({ title, onClose, children, closeLabel }) {
  const ref = useRef(null)
  useEffect(() => {
    const prev = document.activeElement
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
      if (prev && prev.focus) prev.focus()
    }
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 sm:items-center" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
           className="max-h-[88vh] w-full max-w-md overflow-y-auto rounded-t-3xl bg-paper p-5 pb-8 sm:rounded-3xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button type="button" onClick={onClose} aria-label={closeLabel}
                  className="grid h-10 w-10 place-items-center rounded-full text-ink-soft hover:bg-black/5"><IconX /></button>
        </div>
        {children}
      </div>
    </div>
  )
}
