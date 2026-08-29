import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore, getAccessToken } from '@/store/auth'

describe('auth store', () => {
  beforeEach(() => {
    // reset persisted store between tests
    localStorage.clear()
    useAuthStore.setState({ accessToken: null, tenantId: null, email: null, expired: false })
  })

  it('starts unauthenticated', () => {
    expect(useAuthStore.getState().isAuthenticated()).toBe(false)
    expect(getAccessToken()).toBeNull()
  })

  it('stores token + tenant on setAuth and reports authenticated', () => {
    useAuthStore.getState().setAuth('jwt-123', 'tenant-9', 'a@b.com')
    expect(getAccessToken()).toBe('jwt-123')
    expect(useAuthStore.getState().isAuthenticated()).toBe(true)
    expect(useAuthStore.getState().tenantId).toBe('tenant-9')
    expect(useAuthStore.getState().email).toBe('a@b.com')
  })

  it('clears token on logout', () => {
    useAuthStore.getState().setAuth('jwt-123', 'tenant-9')
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().isAuthenticated()).toBe(false)
    expect(getAccessToken()).toBeNull()
  })

  it('setExpired forces unauthenticated and flags expired', () => {
    useAuthStore.getState().setAuth('jwt-123', 'tenant-9')
    useAuthStore.getState().setExpired()
    expect(useAuthStore.getState().isAuthenticated()).toBe(false)
    expect(useAuthStore.getState().expired).toBe(true)
    expect(getAccessToken()).toBeNull()
  })

  it('persists token to localStorage', () => {
    useAuthStore.getState().setAuth('jwt-123', 'tenant-9')
    expect(localStorage.getItem('actready-auth')).toContain('jwt-123')
  })
})
