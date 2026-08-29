import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import { AuthForm } from './AuthForm'

export function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  return (
    <AuthLayout title="Sign in to ActReady" subtitle="See your auditor-traceable readiness score.">
      <AuthForm
        mode="login"
        onSubmit={async (v) => {
          const res = await authApi.login({ email: v.email, password: v.password })
          setAuth(res.access_token, res.tenant_id, v.email)
          navigate('/readiness')
        }}
      />
      <p className="mt-4 text-center text-[13px] text-muted-foreground">
        New here?{' '}
        <Link to="/auth/register" className="font-medium text-primary hover:underline">
          Create a workspace
        </Link>
      </p>
    </AuthLayout>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  return (
    <AuthLayout title="Create your workspace" subtitle="Get a readiness score in under an hour.">
      <AuthForm
        mode="register"
        onSubmit={async (v) => {
          const res = await authApi.register({
            email: v.email,
            password: v.password,
            workspace_name: v.workspace_name ?? 'Workspace',
          })
          setAuth(res.access_token, res.tenant_id, v.email)
          navigate('/readiness')
        }}
      />
      <p className="mt-4 text-center text-[13px] text-muted-foreground">
        Already have an account?{' '}
        <Link to="/auth/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}

/** Shared centered-card layout for auth screens. */
export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-card bg-primary text-lg font-bold text-primary-foreground">
            A
          </div>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">{subtitle}</p>
        </div>
        <div className="rounded-card border border-border bg-white p-6 shadow-sm">{children}</div>
        <p className="mt-4 text-center text-[11px] text-muted-foreground">
          Hint: dev backend may not reject bad creds — adjust once auth lands.
        </p>
      </div>
    </div>
  )
}
