import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Client-only UI state: which of the user's organizations they're
// currently acting in. Not server data -- the source of truth for *which
// organizations exist* is still `/auth/me` / `/organizations`, this store
// only remembers a pointer into that list. See
// docs/05-state-and-data-fetching.md #5.1 and src/store/ui-store.ts for
// the same pattern.

interface WorkspaceState {
  currentOrganizationId: string | null
  setCurrentOrganizationId: (id: string) => void
}

const CURRENT_VERSION = 1

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      currentOrganizationId: null,
      setCurrentOrganizationId: (id) => set({ currentOrganizationId: id }),
    }),
    {
      name: 'neuroflow.workspace',
      version: CURRENT_VERSION,
      migrate: (persistedState) => persistedState as WorkspaceState,
    },
  ),
)
