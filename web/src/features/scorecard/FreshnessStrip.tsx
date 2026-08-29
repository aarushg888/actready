import { AlertTriangle } from 'lucide-react'

/**
 * Freshness strip (FE-1) — surfaces controls at risk of going stale within 30d.
 * Mirrors the engine's 180-day window and the 30-day warning band.
 */
export function FreshnessStrip({ staleWithin30d }: { staleWithin30d: number }) {
  return (
    <div
      className={
        'flex items-center gap-2 rounded-card border px-4 py-3 text-sm ' +
        (staleWithin30d > 0
          ? 'border-status-partial/40 bg-status-partial/5 text-status-partial'
          : 'border-border bg-muted/40 text-muted-foreground')
      }
    >
      <AlertTriangle className="h-4 w-4" />
      {staleWithin30d > 0 ? (
        <span>
          <strong className="font-semibold">{staleWithin30d}</strong> control
          {staleWithin30d === 1 ? '' : 's'} stale within 30 days
        </span>
      ) : (
        <span>No controls approaching the 180-day freshness window</span>
      )}
    </div>
  )
}
