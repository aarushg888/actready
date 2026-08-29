import { create } from 'zustand'
import type { ControlStatus, Framework } from '@/lib/types'

/**
 * Thin UI state for the Control Library + Detail Drawer (FE-2/D3/E1).
 * TanStack Query owns all server data; this only holds local view state.
 */
export interface ControlFilters {
  statuses: ControlStatus[] // empty = all
  framework: Framework | 'all'
  query: string
  sortBy: 'id' | 'name' | 'status' | 'evidence_count' | 'evidence_age_days'
  sortDir: 'asc' | 'desc'
}

interface UIState {
  filters: ControlFilters
  selectedControlId: string | null
  setStatuses: (s: ControlStatus[]) => void
  toggleStatus: (s: ControlStatus) => void
  setFramework: (f: Framework | 'all') => void
  setQuery: (q: string) => void
  setSort: (by: ControlFilters['sortBy']) => void
  openControl: (id: string) => void
  closeControl: () => void
}

const DEFAULT_FILTERS: ControlFilters = {
  statuses: [],
  framework: 'all',
  query: '',
  sortBy: 'status',
  sortDir: 'asc',
}

export const useControlStore = create<UIState>((set) => ({
  filters: DEFAULT_FILTERS,
  selectedControlId: null,
  setStatuses: (statuses) => set((s) => ({ filters: { ...s.filters, statuses } })),
  toggleStatus: (status) =>
    set((s) => {
      const has = s.filters.statuses.includes(status)
      const statuses = has
        ? s.filters.statuses.filter((x) => x !== status)
        : [...s.filters.statuses, status]
      return { filters: { ...s.filters, statuses } }
    }),
  setFramework: (framework) => set((s) => ({ filters: { ...s.filters, framework } })),
  setQuery: (query) => set((s) => ({ filters: { ...s.filters, query } })),
  setSort: (sortBy) =>
    set((s) => {
      const same = s.filters.sortBy === sortBy
      const sortDir = same && s.filters.sortDir === 'asc' ? 'desc' : 'asc'
      return { filters: { ...s.filters, sortBy, sortDir } }
    }),
  openControl: (selectedControlId) => set({ selectedControlId }),
  closeControl: () => set({ selectedControlId: null }),
}))
