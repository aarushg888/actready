import type { EvidenceType } from '@/lib/types'

/** Map an uploaded file to the engine's 4 evidence types by suffix (INT-4). */
export function inferEvidenceType(filename: string): EvidenceType | undefined {
  const lower = filename.toLowerCase()
  if (lower.endsWith('.json')) return 'eval_run' // eval/promptfoo JSON most common
  if (lower.endsWith('.yaml') || lower.endsWith('.yml')) {
    // model card vs policy both YAML — default policy, user can override
    return 'model_card'
  }
  if (lower.endsWith('.csv')) return 'incident_log'
  return undefined
}

export const EVIDENCE_TYPE_OPTIONS: { value: EvidenceType; label: string; hint: string }[] = [
  { value: 'model_card', label: 'Model card', hint: '.yaml / .yml' },
  { value: 'eval_run', label: 'Eval run', hint: '.json' },
  { value: 'incident_log', label: 'Incident log', hint: '.csv' },
  { value: 'policy', label: 'Policy', hint: '.yaml / .yml' },
]
