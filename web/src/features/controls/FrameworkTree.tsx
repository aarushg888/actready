import type { ControlItem, Framework } from '@/lib/types'
import { cn } from '@/lib/utils'
import { frameworkGroupOf } from './grouping'

/**
 * Left-rail framework tree (FE-2). Groups controls by framework + annex/section
 * so the user can filter the table by clicking a node.
 */
export function FrameworkTree({
  items,
  framework,
  onSelect,
}: {
  items: ControlItem[]
  framework: Framework | 'all'
  onSelect: (f: Framework | 'all') => void
}) {
  const byFramework = (f: Framework) => items.filter((i) => i.framework === f)
  return (
    <nav className="space-y-4 text-[13px]">
      <TreeButton label="All frameworks" active={framework === 'all'} onClick={() => onSelect('all')} count={items.length} />
      <TreeSection
        label="ISO 42001"
        items={byFramework('iso42001')}
        onSelect={onSelect}
        framework="iso42001"
        current={framework}
      />
      <TreeSection
        label="EU AI Act"
        items={byFramework('eu_ai_act')}
        onSelect={onSelect}
        framework="eu_ai_act"
        current={framework}
      />
    </nav>
  )
}

function TreeSection({
  label,
  items,
  onSelect,
  framework,
  current,
}: {
  label: string
  items: ControlItem[]
  onSelect: (f: Framework | 'all') => void
  framework: Framework
  current: Framework | 'all'
}) {
  const groups = new Map<string, number>()
  for (const it of items) groups.set(frameworkGroupOf(it), (groups.get(frameworkGroupOf(it)) ?? 0) + 1)
  return (
    <div>
      <TreeButton label={label} active={current === framework} onClick={() => onSelect(framework)} count={items.length} />
      <div className="ml-3 mt-1 space-y-0.5 border-l border-border pl-2">
        {[...groups.entries()].map(([g, n]) => (
          <div key={g} className="flex items-center justify-between rounded-chip px-2 py-1 text-muted-foreground hover:bg-muted">
            <span className="truncate">{g}</span>
            <span className="font-mono text-[11px]">{n}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function TreeButton({
  label,
  active,
  onClick,
  count,
}: {
  label: string
  active: boolean
  onClick: () => void
  count?: number
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center justify-between rounded-chip px-2 py-1.5 text-left font-medium transition-colors',
        active ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-muted',
      )}
    >
      <span>{label}</span>
      {count !== undefined && <span className="font-mono text-[11px] opacity-70">{count}</span>}
    </button>
  )
}
