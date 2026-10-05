import { Card } from './ui.jsx'

export const Bar = ({ className = '' }) => <div className={`skeleton ${className}`} />

export function HeroSkeleton({ label }) {
  return (
    <div role="status" aria-label={label} className="rounded-3xl bg-white p-5 shadow-card">
      <Bar className="mb-5 h-8 w-40" />
      <div className="mx-auto mb-4 h-44 w-44 rounded-full skeleton" />
      <Bar className="mx-auto h-5 w-32" />
    </div>
  )
}

export function CardSkeleton({ lines = 4, label }) {
  return (
    <Card role="status" aria-label={label}>
      <Bar className="mb-4 h-5 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Bar key={i} className={`mb-2.5 h-4 ${i % 2 ? 'w-4/5' : 'w-full'}`} />
      ))}
    </Card>
  )
}
