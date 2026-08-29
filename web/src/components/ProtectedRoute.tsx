import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'

/** Gates app routes — bounces to /auth/login when unauthenticated or expired. */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  const expired = useAuthStore((s) => s.expired)
  const location = useLocation()

  if (!token || expired) {
    return <Navigate to="/auth/login" replace state={{ from: location.pathname }} />
  }
  return <>{children}</>
}
