import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'
import { STATUS_LABELS, type ControlStatus } from '@/lib/types'

const styles: Record<ControlStatus, string> = {
  satisfied: 'bg-status-satisfied text-status-satisfied-fg',
  partial: 'bg-status-partial text-status-partial-fg',
  missing: 'bg-status-missing text-status-missing-fg',
}

export function StatusChip({
  status,
  className,
  children,
}: {
  status: ControlStatus
  className?: string
  children?: ReactNode
}) {
  return (
    <span className={cn('status-chip', styles[status], className)}>
      {children ?? STATUS_LABELS[status]}
    </span>
  )
}

/** Solid dot in the semantic color — used in compact lists. */
export function StatusDot({ status, className }: { status: ControlStatus; className?: string }) {
  return (
    <span
      className={cn('inline-block h-2 w-2 rounded-full', className)}
      style={{
        backgroundColor: `hsl(var(--status-${status}))`,
      }}
      aria-hidden
    />
  )
}
