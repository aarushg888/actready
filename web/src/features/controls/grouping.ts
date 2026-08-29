import type { ControlItem } from '@/lib/types'

/** Map a control to its framework group label used in the left-rail tree (FE-2). */
export function frameworkGroupOf(c: ControlItem): string {
  if (c.framework === 'iso42001') {
    // ISO 42001 Annex A groups are prefixed A.2–A.10
    const m = c.control_id.match(/^A\.(\d+)/)
    if (m) return `A.${m[1]} — ${ISO_GROUPS[m[1]] ?? 'Annex A'}`
    return 'ISO 42001'
  }
  const m = c.control_id.match(/^ART(\d+)/i)
  if (m) return `Article ${m[1]}`
  return 'EU AI Act'
}

const ISO_GROUPS: Record<string, string> = {
  '2': 'Organizational roles',
  '3': 'Resources',
  '4': 'Competencies',
  '5': 'AI system lifecycle',
  '6': 'Data',
  '7': 'Information security',
  '8': 'Supplier relationships',
  '9': 'Operational cybersecurity',
  '10': 'Third-party',
}
