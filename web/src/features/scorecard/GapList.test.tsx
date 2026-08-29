import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusChip } from '@/components/ui/StatusChip'
import { GapList } from '@/features/scorecard/GapList'
import type { ControlItem } from '@/lib/types'

const item = (over: Partial<ControlItem>): ControlItem => ({
  control_id: 'A.6.3',
  control_name: 'Data quality',
  framework: 'iso42001',
  obligation_ids: ['ART13'],
  status: 'missing',
  evidence_count: 0,
  evidence_age_days: null,
  owner: null,
  remediation_hint: '',
  review_counsel: false,
  ...over,
})

describe('StatusChip', () => {
  it('renders the status label', () => {
    render(<StatusChip status="satisfied" />)
    expect(screen.getByText('Satisfied')).toBeInTheDocument()
  })
  it('renders custom children', () => {
    render(<StatusChip status="partial">2 partial</StatusChip>)
    expect(screen.getByText('2 partial')).toBeInTheDocument()
  })
})

describe('GapList (worst-first)', () => {
  it('sorts missing before partial', () => {
    const items = [
      item({ control_id: 'B.1', status: 'partial', control_name: 'Partial control' }),
      item({ control_id: 'A.1', status: 'missing', control_name: 'Missing control' }),
    ]
    render(<GapList items={items} onSelect={() => {}} />)
    const list = screen.getByText('Missing control').closest('li')!
    const all = Array.from(document.querySelectorAll('li'))
    expect(all.indexOf(list)).toBe(0)
  })
})
