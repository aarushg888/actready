import { useState, type ReactNode } from 'react'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input, Label } from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'At least 8 characters'),
})
const registerSchema = loginSchema.extend({
  workspace_name: z.string().min(2, 'Workspace name is required'),
})

type Mode = 'login' | 'register'

/**
 * Shared login/register form. Validates with Zod, reports server errors inline,
 * redirects to /readiness on success via the onSubmit callback.
 */
export function AuthForm({ mode, onSubmit }: { mode: Mode; onSubmit: (v: { email: string; password: string; workspace_name?: string }) => void }) {
  const [values, setValues] = useState({ email: '', password: '', workspace_name: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const set = (k: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [k]: e.target.value }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setServerError(null)
    const schema = mode === 'login' ? loginSchema : registerSchema
    const parsed = schema.safeParse(values)
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {}
      for (const issue of parsed.error.issues) {
        fieldErrors[String(issue.path[0])] = issue.message
      }
      setErrors(fieldErrors)
      return
    }
    setErrors({})
    setPending(true)
    try {
      await onSubmit(parsed.data)
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setPending(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {mode === 'register' && (
        <Field label="Workspace name" error={errors.workspace_name}>
          <Input
            value={values.workspace_name}
            onChange={set('workspace_name')}
            placeholder="Acme AI"
            autoComplete="organization"
          />
        </Field>
      )}
      <Field label="Email" error={errors.email}>
        <Input
          type="email"
          value={values.email}
          onChange={set('email')}
          placeholder="you@company.com"
          autoComplete="email"
        />
      </Field>
      <Field label="Password" error={errors.password}>
        <Input
          type="password"
          value={values.password}
          onChange={set('password')}
          placeholder="••••••••"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
        />
      </Field>
      {serverError && (
        <p className="rounded-chip bg-status-missing/10 px-3 py-2 text-[13px] text-status-missing">
          {serverError}
        </p>
      )}
      <Button type="submit" className="w-full" disabled={pending} size="lg">
        {pending && <Spinner />}
        {mode === 'login' ? 'Sign in' : 'Create workspace'}
      </Button>
    </form>
  )
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
      {error && <p className="mt-1 text-[12px] text-status-missing">{error}</p>}
    </div>
  )
}
