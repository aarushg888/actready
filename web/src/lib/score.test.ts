import { describe, it, expect } from 'vitest'
import { roundScore, donutSegments, statusWeight } from '@/lib/score'
import type { ReadinessResponse } from '@/lib/types'

describe('roundScore', () => {
  it('rounds to nearest integer', () => {
    expect(roundScore(41.4)).toBe(41)
    expect(roundScore(41.6)).toBe(42)
  })
  it('clamps to 0..100', () => {
    expect(roundScore(-5)).toBe(0)
    expect(roundScore(150)).toBe(100)
  })
  it('handles NaN', () => {
    expect(roundScore(NaN)).toBe(0)
  })
})

describe('donutSegments', () => {
  const base: ReadinessResponse = {
    readiness_score: 50,
    total: 10,
    satisfied: 4,
    partial: 2,
    missing: 4,
    freshness_window_days: 180,
    as_of: '2026-08-29',
    frameworks: {
      iso42001: { satisfied: 2, partial: 1, missing: 2 },
      eu_ai_act: { satisfied: 2, partial: 1, missing: 2 },
    },
    stale_within_30d: 1,
    last_assessed_at: null,
  }

  it('produces green/amber/red segments with correct fractions', () => {
    const segs = donutSegments(base)
    expect(segs).toHaveLength(3)
    expect(segs[0]).toMatchObject({ name: 'Satisfied', value: 4, fraction: 0.4 })
    expect(segs[1]).toMatchObject({ name: 'Partial', value: 2, fraction: 0.2 })
    expect(segs[2]).toMatchObject({ name: 'Missing', value: 4, fraction: 0.4 })
  })

  it('never divides by zero', () => {
    const zero: ReadinessResponse = { ...base, total: 0, satisfied: 0, partial: 0, missing: 0 }
    const segs = donutSegments(zero)
    expect(segs.every((s) => s.fraction === 0)).toBe(true)
  })
})

describe('statusWeight (worst-first ordering)', () => {
  it('orders missing > partial > satisfied', () => {
    expect(statusWeight('missing')).toBeGreaterThan(statusWeight('partial'))
    expect(statusWeight('partial')).toBeGreaterThan(statusWeight('satisfied'))
  })
})
