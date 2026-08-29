/**
 * ActReady v0.2 API contract types.
 *
 * Hand-written from the GapReport / GapItem shapes in the engine
 * (`api/app/mapper.py`, `api/app/models.py`) and the contract in
 * `docs/planning/frontend-plan.md` §2. Kept in sync with the backend by
 * convention (openapi-typescript generation is the future CI step).
 */

export type Framework = 'iso42001' | 'eu_ai_act'
export type ControlStatus = 'satisfied' | 'partial' | 'missing'
export type EvidenceType = 'model_card' | 'eval_run' | 'incident_log' | 'policy'
export type IngestStatus = 'processing' | 'ingested' | 'failed'

export const FRAMEWORK_LABELS: Record<Framework, string> = {
  iso42001: 'ISO 42001',
  eu_ai_act: 'EU AI Act',
}

export const STATUS_LABELS: Record<ControlStatus, string> = {
  satisfied: 'Satisfied',
  partial: 'Partial',
  missing: 'Missing',
}

// ---- Auth ----------------------------------------------------------------

export interface LoginRequest {
  email: string
  password: string
}
export interface RegisterRequest {
  email: string
  password: string
  workspace_name: string
}
export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  tenant_id: string
}

// ---- Readiness scorecard (GET /api/readiness) ----------------------------

export interface FrameworkBreakdown {
  satisfied: number
  partial: number
  missing: number
}
export interface ReadinessResponse {
  readiness_score: number // 0–100, engine: (satisfied + 0.5*partial)/total
  total: number // controls assessed (39 ISO + 21 AI Act in catalog)
  satisfied: number
  partial: number
  missing: number
  freshness_window_days: number // 180
  as_of: string // ISO date
  frameworks: {
    iso42001: FrameworkBreakdown
    eu_ai_act: FrameworkBreakdown
  }
  stale_within_30d: number // freshness strip
  last_assessed_at: string | null // timestamp of latest snapshot
}

// ---- Control library (GET /api/controls) ---------------------------------

export interface ControlItem {
  control_id: string // e.g. "A.6.3"
  control_name: string
  framework: Framework
  obligation_ids: string[] // e.g. ["ART13"]
  status: ControlStatus
  evidence_count: number
  evidence_age_days: number | null // null = no evidence
  owner: string | null
  remediation_hint: string // engine string, empty when satisfied
  review_counsel: boolean // uncertain mapping flag
}

// ---- Control detail (GET /api/controls/:id) ------------------------------

export interface Obligation {
  id: string
  article: number
  title: string
  source_url: string
}
export interface LinkedEvidence {
  id: string
  type: EvidenceType
  source: string
  collected_at: string
}
export interface ControlHistoryEntry {
  status: string
  changed_at: string
}
export interface ControlDetail extends ControlItem {
  obligations: Obligation[]
  freshness: {
    collected_at: string | null
    age_days: number | null
    stale_in_days: number | null
  }
  linked_evidence: LinkedEvidence[]
  history: ControlHistoryEntry[]
}

// ---- Evidence (POST /api/evidence, GET /api/evidence/:id) -----------------

export interface EvidenceArtifact {
  id: string
  evidence_type: EvidenceType
  source: string // "manual:filename.yaml"
  ingest_status: IngestStatus
  content_hash: string // sha256
  collected_at: string
  error?: string
}
