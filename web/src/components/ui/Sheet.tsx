import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Right-side drawer (shadcn Sheet pattern, hand-rolled to avoid Radix install).
 * Closes on Esc or overlay click. Rendered into document.body via portal.
 */
export function Sheet({
  open,
  onClose,
  title,
  children,
  width = 'max-w-md',
}: {
  open: boolean
  onClose: () => void
  title?: ReactNode
  children: ReactNode
  width?: string
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/30 animate-in fade-in"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative h-full w-full bg-white shadow-xl animate-in slide-in-from-right',
          width,
        )}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <div className="min-w-0">{title}</div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-chip p-1 text-muted-foreground hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="h-[calc(100%-49px)] overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
