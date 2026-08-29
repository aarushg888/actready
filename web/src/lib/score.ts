import type { ReadinessResponse } from '@/lib/types'

/** Pure helper: clamp a 0–100 readiness score and round to an integer. */
export function roundScore(score: number): number {
  if (Number.isNaN(score)) return 0
  return Math.max(0, Math.min(100, Math.round(score)))
}

/**
 * Derive a donut segment breakdown from a readiness response:
 * satisfied (green), partial (amber), missing (red) as fractions of total.
 * `partial` is weighted 0.5 in the headline score but shown at full count in
 * the donut so the breakdown is the true assessable population.
 */
export function donutSegments(r: ReadinessResponse) {
  const total = r.total || 1
  return [
    { name: 'Satisfied', value: r.satisfied, color: 'hsl(var(--status-satisfied))' },
    { name: 'Partial', value: r.partial, color: 'hsl(var(--status-partial))' },
    { name: 'Missing', value: r.missing, color: 'hsl(var(--status-missing))' },
  ].map((s) => ({ ...s, fraction: s.value / total }))
}

/** Status label for the worst-first ordering used in the gaps list. */
export function statusWeight(status: 'satisfied' | 'partial' | 'missing'): number {
  return status === 'missing' ? 2 : status === 'partial' ? 1 : 0
}
