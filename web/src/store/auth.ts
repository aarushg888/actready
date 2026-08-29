import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/** Thin client auth state — JWT in memory + localStorage; TanStack Query owns server data. */
interface AuthState {
  accessToken: string | null
  tenantId: string | null
  email: string | null
  /** Set after a 401 so the shell can force a redirect to /auth/login. */
  expired: boolean
  setAuth: (token: string, tenantId: string, email?: string) => void
  setExpired: () => void
  logout: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      tenantId: null,
      email: null,
      expired: false,
      setAuth: (token, tenantId, email) =>
        set({ accessToken: token, tenantId, email: email ?? get().email, expired: false }),
      setExpired: () => set({ accessToken: null, expired: true }),
      logout: () => set({ accessToken: null, tenantId: null, email: null, expired: false }),
      isAuthenticated: () => Boolean(get().accessToken),
    }),
    {
      name: 'actready-auth',
      partialize: (s) => ({
        accessToken: s.accessToken,
        tenantId: s.tenantId,
        email: s.email,
      }),
    },
  ),
)

/**
 * Read the current bearer token from the store. Exported as a plain function
 * so the fetch wrapper and tests can grab it without subscribing to React.
 */
export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken
}
