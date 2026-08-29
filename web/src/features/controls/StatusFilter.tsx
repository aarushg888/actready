import type { ControlStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

const ALL: ControlStatus[] = ['satisfied', 'partial', 'missing']

/** Multi-select status toggle chips (FE-2). Empty = all. */
export function StatusFilter({
  selected,
  onToggle,
}: {
  selected: ControlStatus[]
  onToggle: (s: ControlStatus) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {ALL.map((s) => {
        const active = selected.includes(s)
        return (
          <button
            key={s}
            type="button"
            onClick={() => onToggle(s)}
            className={cn(
              'rounded-chip border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors',
              active
                ? statusActiveClass(s)
                : 'border-border bg-white text-muted-foreground hover:bg-muted',
            )}
          >
            {s}
          </button>
        )
      })}
      {selected.length > 0 && (
        <button
          type="button"
          onClick={() => ALL.forEach((s) => selected.includes(s) && onToggle(s))}
          className="ml-1 text-[12px] text-muted-foreground hover:underline"
        >
          clear
        </button>
      )}
    </div>
  )
}

function statusActiveClass(s: ControlStatus): string {
  if (s === 'satisfied') return 'border-status-satisfied bg-status-satisfied text-status-satisfied-fg'
  if (s === 'partial') return 'border-status-partial bg-status-partial text-status-partial-fg'
  return 'border-status-missing bg-status-missing text-status-missing-fg'
}
