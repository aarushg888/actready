import type { FrameworkBreakdown } from '@/lib/types'
import { StatusChip } from '@/components/ui/StatusChip'

/** Compact satisfied/partial/missing chip breakdown for one framework (FE-1). */
export function FrameworkCard({
  title,
  breakdown,
}: {
  title: string
  breakdown: FrameworkBreakdown
}) {
  const total = breakdown.satisfied + breakdown.partial + breakdown.missing || 1
  return (
    <div className="rounded-card border border-border bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="font-mono text-[13px] text-muted-foreground">
          {Math.round(((breakdown.satisfied + 0.5 * breakdown.partial) / total) * 100)}%
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <StatusChip status="satisfied">{breakdown.satisfied} satisfied</StatusChip>
        <StatusChip status="partial">{breakdown.partial} partial</StatusChip>
        <StatusChip status="missing">{breakdown.missing} missing</StatusChip>
      </div>
    </div>
  )
}
