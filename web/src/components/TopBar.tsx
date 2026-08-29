import { useAuthStore } from '@/store/auth'
import { useRerunAssessment } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { LogOut, RefreshCw } from 'lucide-react'

export function TopBar() {
  const email = useAuthStore((s) => s.email)
  const logout = useAuthStore((s) => s.logout)
  const rerun = useRerunAssessment()

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-white px-5">
      <div className="flex items-center gap-3">
        <span className="text-[13px] font-medium text-muted-foreground">Workspace</span>
        <span className="text-sm font-semibold">ActReady</span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => rerun.mutate()}
          disabled={rerun.isPending}
        >
          {rerun.isPending ? <Spinner /> : <RefreshCw className="h-3.5 w-3.5" />}
          Re-run
        </Button>
        <div className="flex items-center gap-2 border-l border-border pl-3">
          <span className="text-[13px] text-muted-foreground">{email ?? 'signed in'}</span>
          <button
            type="button"
            onClick={logout}
            className="rounded-chip p-1.5 text-muted-foreground hover:bg-muted"
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  )
}
