import { NavLink } from 'react-router-dom'
import { Gauge, ListChecks, Database, FileDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/readiness', label: 'Readiness', icon: Gauge },
  { to: '/controls', label: 'Controls', icon: ListChecks },
  { to: '/evidence', label: 'Evidence', icon: Database },
  { to: '/export', label: 'Export', icon: FileDown },
]

export function Sidebar() {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-muted/40">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-card bg-primary text-sm font-bold text-primary-foreground">
          A
        </div>
        <span className="text-sm font-semibold tracking-tight">ActReady</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-chip px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-foreground hover:bg-muted',
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border p-3 text-[11px] text-muted-foreground">
        v0.2 · readiness you can audit
      </div>
    </aside>
  )
}
