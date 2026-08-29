import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAccessToken, useAuthStore } from '@/store/auth'
import type {
  AuthResponse,
  ControlDetail,
  ControlItem,
  ControlStatus,
  EvidenceArtifact,
  EvidenceType,
  Framework,
  LoginRequest,
  ReadinessResponse,
  RegisterRequest,
} from '@/lib/types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

/** Custom error carrying the HTTP status so callers can branch (e.g. 401). */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })

  if (res.status === 401) {
    // Token rejected/expired — force the shell to bounce to login.
    useAuthStore.getState().setExpired()
    throw new ApiError(401, 'Session expired or invalid credentials')
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  const ct = res.headers.get('content-type') ?? ''
  if (ct.includes('application/json')) return (await res.json()) as T
  return (await res.text()) as T as T
}

// ---- Auth ----------------------------------------------------------------

export const authApi = {
  login: (body: LoginRequest) =>
    request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  register: (body: RegisterRequest) =>
    request<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
}

// ---- Readiness -----------------------------------------------------------

export function useReadiness() {
  return useQuery({
    queryKey: ['readiness'],
    queryFn: () => request<ReadinessResponse>('/readiness'),
  })
}

// ---- Controls ------------------------------------------------------------

export interface ControlsParams {
  status?: ControlStatus | ControlStatus[]
  framework?: Framework | 'all'
  q?: string
}

function buildControlsQuery(params: ControlsParams): string {
  const sp = new URLSearchParams()
  const status = params.status
  if (status) {
    const list = Array.isArray(status) ? status : [status]
    if (list.length) sp.set('status', list.join(','))
  }
  if (params.framework && params.framework !== 'all') sp.set('framework', params.framework)
  if (params.q) sp.set('q', params.q)
  const qs = sp.toString()
  return qs ? `?${qs}` : ''
}

export function useControls(params: ControlsParams = {}) {
  return useQuery({
    queryKey: ['controls', params],
    queryFn: () => request<ControlItem[]>(`/controls${buildControlsQuery(params)}`),
  })
}

export function useControlDetail(id: string | null) {
  return useQuery({
    queryKey: ['control', id],
    queryFn: () => request<ControlDetail>(`/controls/${id}`),
    enabled: Boolean(id),
  })
}

/** Worst-first gaps = missing then partial, used by the scorecard list. */
export function useGaps() {
  return useQuery({
    queryKey: ['controls', 'gaps'],
    queryFn: () =>
      request<ControlItem[]>('/controls?status=missing,partial').then((items) =>
        [...items].sort((a, b) => statusRank(b.status) - statusRank(a.status)),
      ),
  })
}

function statusRank(s: ControlStatus): number {
  return s === 'missing' ? 2 : s === 'partial' ? 1 : 0
}

// ---- Re-run --------------------------------------------------------------

export function useRerunAssessment() {
  const qc = useQueryClient()
  return useMutation({
    // The backend re-runs the engine on demand; until a dedicated endpoint
    // exists we simply invalidate the derived data so it refetches.
    mutationFn: async () => {
      await request<{ ok: boolean }>('/readiness', { method: 'POST' }).catch(() => undefined)
      return true
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['controls'] })
    },
  })
}

// ---- Evidence ------------------------------------------------------------

export function useUploadEvidence() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (input: { file: File; evidence_type?: EvidenceType; control_id?: string }) => {
      const fd = new FormData()
      fd.append('file', input.file)
      if (input.evidence_type) fd.append('evidence_type', input.evidence_type)
      if (input.control_id) fd.append('control_id', input.control_id)
      return request<EvidenceArtifact>('/evidence', { method: 'POST', body: fd })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['controls'] })
    },
  })
}

export function useEvidence(id: string | null) {
  return useQuery({
    queryKey: ['evidence', id],
    queryFn: () => request<EvidenceArtifact>(`/evidence/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const data = query.state.data as EvidenceArtifact | undefined
      if (!data || data.ingest_status === 'processing') return 1500
      return false
    },
  })
}

// ---- Report export -------------------------------------------------------

export async function fetchReport(format: 'markdown' | 'json' | 'pdf'): Promise<string> {
  return request<string>(`/report?format=${format}`)
}

export async function fetchReportJson(): Promise<unknown> {
  return request<unknown>('/report?format=json')
}
