import type { ControlItem } from '@/lib/types'
import { StatusChip } from '@/components/ui/StatusChip'
import { statusWeight } from '@/lib/score'

/** Worst-first gaps list (FE-1): missing → partial, each row opens the drawer. */
export function GapList({
  items,
  onSelect,
}: {
  items: ControlItem[]
  onSelect: (id: string) => void
}) {
  const sorted = [...items].sort((a, b) => statusWeight(b.status) - statusWeight(a.status))
  return (
    <ul className="divide-y divide-border">
      {sorted.map((c) => (
        <li key={c.control_id}>
          <button
            type="button"
            onClick={() => onSelect(c.control_id)}
            className="flex w-full items-center justify-between gap-3 px-1 py-2.5 text-left hover:bg-muted/50"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[13px] font-medium text-foreground">
                  {c.control_id}
                </span>
                <span className="truncate text-[13px] text-muted-foreground">
                  {c.control_name}
                </span>
              </div>
              {c.remediation_hint && (
                <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
                  {c.remediation_hint}
                </p>
              )}
            </div>
            <StatusChip status={c.status} />
          </button>
        </li>
      ))}
    </ul>
  )
}
