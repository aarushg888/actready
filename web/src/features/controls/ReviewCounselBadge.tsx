import { Scale } from 'lucide-react'

/** Amber "needs legal review" callout (FE-3 / FR §5.8 REVIEW-COUNSEL). */
export function ReviewCounselBadge() {
  return (
    <div className="flex items-start gap-2 rounded-card border border-status-partial/50 bg-status-partial/10 px-3 py-2.5 text-[13px] text-status-partial">
      <Scale className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <p className="font-semibold">Needs legal review</p>
        <p className="mt-0.5 text-[12px] opacity-90">
          The engine flagged this control→obligation mapping as uncertain. Confirm before relying on it in an audit.
        </p>
      </div>
    </div>
  )
}
