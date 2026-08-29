import { useControls } from '@/lib/api'
import { useControlStore } from '@/store/ui'
import { FrameworkTree } from './FrameworkTree'
import { StatusFilter } from './StatusFilter'
import { ControlTable } from './ControlTable'
import { Input } from '@/components/ui/Input'
import { Search } from 'lucide-react'
import { ErrorState, LoadingState, EmptyState } from '@/components/ui/Spinner'

export function ControlsPage() {
  const filters = useControlStore((s) => s.filters)
  const setFramework = useControlStore((s) => s.setFramework)
  const toggleStatus = useControlStore((s) => s.toggleStatus)
  const setQuery = useControlStore((s) => s.setQuery)
  const openControl = useControlStore((s) => s.openControl)

  const { data, isLoading, isError, error, refetch } = useControls({
    status: filters.statuses.length ? filters.statuses : undefined,
    framework: filters.framework,
    q: filters.query || undefined,
  })

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Control Library</h1>
        <p className="text-[13px] text-muted-foreground">
          Derived from your evidence — not asserted. Click a row for detail.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <aside className="rounded-card border border-border bg-muted/30 p-3">
          {isLoading ? (
            <p className="text-[13px] text-muted-foreground">Loading tree…</p>
          ) : data ? (
            <FrameworkTree items={data} framework={filters.framework} onSelect={setFramework} />
          ) : null}
        </aside>

        <div className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-xs">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={filters.query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search controls…"
                className="pl-8"
              />
            </div>
            <StatusFilter selected={filters.statuses} onToggle={toggleStatus} />
          </div>

          {isLoading ? (
            <LoadingState label="Loading controls…" />
          ) : isError ? (
            <ErrorState message={error instanceof Error ? error.message : 'Failed'} onRetry={() => refetch()} />
          ) : data && data.length > 0 ? (
            <ControlTable items={data} onSelect={openControl} />
          ) : (
            <EmptyState
              title="No controls match your filter"
              hint="Clear the status filter or search to see everything."
            />
          )}
        </div>
      </div>
    </div>
  )
}
