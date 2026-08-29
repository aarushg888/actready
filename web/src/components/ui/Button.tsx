import { cn } from '@/lib/utils'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  children?: ReactNode
}

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50',
  secondary: 'bg-muted text-foreground hover:bg-border disabled:opacity-50',
  ghost: 'bg-transparent text-foreground hover:bg-muted disabled:opacity-50',
  danger: 'bg-status-missing text-status-missing-fg hover:opacity-90 disabled:opacity-50',
  outline: 'border border-border bg-transparent text-foreground hover:bg-muted disabled:opacity-50',
}

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-[13px]',
  md: 'h-9 px-4 text-sm',
  lg: 'h-10 px-5 text-sm',
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-chip font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
