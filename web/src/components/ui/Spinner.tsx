import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('h-4 w-4 animate-spin', className)} aria-hidden />
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
      <Spinner />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="rounded-card border border-status-missing/40 bg-status-missing/5 px-4 py-3 text-sm text-status-missing">
      <p className="font-medium">Something went wrong</p>
      <p className="mt-0.5 text-[13px]">{message}</p>
      {onRetry && (
        <button
          className="mt-2 text-[13px] font-medium underline"
          onClick={onRetry}
          type="button"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string
  hint?: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-border px-4 py-12 text-center">
      <p className="text-sm font-medium text-foreground">{title}</p>
      {hint && <p className="max-w-sm text-[13px] text-muted-foreground">{hint}</p>}
      {action}
    </div>
  )
}
