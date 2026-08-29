import type { ControlItem } from '@/lib/types'
import { StatusChip } from '@/components/ui/StatusChip'
import { useControlStore } from '@/store/ui'
import type { ControlFilters } from '@/store/ui'
import { cn } from '@/lib/utils'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

type SortKey = ControlFilters['sortBy']

const COLUMNS: { key: SortKey | 'owner'; label: string; className?: string; sortable?: boolean }[] = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'Control' },
  { key: 'status', label: 'Status' },
  { key: 'evidence_count', label: 'Evidence', className: 'text-right' },
  { key: 'evidence_age_days', label: 'Age', className: 'text-right' },
  { key: 'owner', label: 'Owner', sortable: false },
]

/** Dense, sortable control table (FE-2). Row click opens the detail drawer. */
export function ControlTable({
  items,
  onSelect,
}: {
  items: ControlItem[]
  onSelect: (id: string) => void
}) {
  const sortBy = useControlStore((s) => s.filters.sortBy)
  const sortDir = useControlStore((s) => s.filters.sortDir)
  const setSort = useControlStore((s) => s.setSort)

  const sorted = [...items].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1
    switch (sortBy) {
      case 'id':
        return a.control_id.localeCompare(b.control_id) * dir
      case 'name':
        return a.control_name.localeCompare(b.control_name) * dir
      case 'status':
        return (statusRank(a.status) - statusRank(b.status)) * dir
      case 'evidence_count':
        return (a.evidence_count - b.evidence_count) * dir
      case 'evidence_age_days':
        return ((a.evidence_age_days ?? 9999) - (b.evidence_age_days ?? 9999)) * dir
      default:
        return 0
    }
  })

  return (
    <div className="overflow-hidden rounded-card border border-border">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-border bg-muted/40 text-muted-foreground">
            {COLUMNS.map((col) => {
              const isSortable = col.sortable !== false
              return (
                <th
                  key={col.key}
                  className={cn('px-3 py-2 font-medium', col.className ?? 'text-left')}
                >
                  {isSortable ? (
                    <button
                      type="button"
                      onClick={() => setSort(col.key as SortKey)}
                      className={cn(
                        'inline-flex items-center gap-1 hover:text-foreground',
                        col.className === 'text-right' && 'flex-row-reverse',
                      )}
                    >
                      {col.label}
                      {sortBy === col.key ? (
                        sortDir === 'asc' ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : (
                          <ArrowDown className="h-3 w-3" />
                        )
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </button>
                  ) : (
                    <span>{col.label}</span>
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => (
            <tr
              key={c.control_id}
              onClick={() => onSelect(c.control_id)}
              className="h-11 cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
            >
              <td className="px-3 font-mono font-medium text-foreground">{c.control_id}</td>
              <td className="px-3">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-foreground">{c.control_name}</span>
                  {c.review_counsel && (
                    <span
                      title="Needs legal review (REVIEW-COUNSEL)"
                      className="rounded-chip bg-status-partial/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-status-partial"
                    >
                      review
                    </span>
                  )}
                </div>
              </td>
              <td className="px-3">
                <StatusChip status={c.status} />
              </td>
              <td className="px-3 text-right font-mono">{c.evidence_count}</td>
              <td className="px-3 text-right font-mono text-muted-foreground">
                {c.evidence_age_days ?? '—'}
              </td>
              <td className="px-3 text-muted-foreground">{c.owner ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function statusRank(s: 'satisfied' | 'partial' | 'missing'): number {
  return s === 'missing' ? 2 : s === 'partial' ? 1 : 0
}
