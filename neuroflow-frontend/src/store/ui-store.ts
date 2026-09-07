import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Client-only UI state -- never server data (docs/05-state-and-data-fetching.md #5.1).
// Persisted with an explicit version + migrate function from day one: a
// persisted store without a migration path breaks for every existing user
// the first time its shape changes.

interface UiState {
  inspectorWidth: number
  bottomPanelHeight: number
  activeInspectorTab: 'params' | 'input' | 'output'
  setInspectorWidth: (width: number) => void
  setBottomPanelHeight: (height: number) => void
  setActiveInspectorTab: (tab: UiState['activeInspectorTab']) => void
}

const CURRENT_VERSION = 1

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      inspectorWidth: 420,
      bottomPanelHeight: 240,
      activeInspectorTab: 'params',
      setInspectorWidth: (width) => set({ inspectorWidth: width }),
      setBottomPanelHeight: (height) => set({ bottomPanelHeight: height }),
      setActiveInspectorTab: (tab) => set({ activeInspectorTab: tab }),
    }),
    {
      name: 'neuroflow.ui',
      version: CURRENT_VERSION,
      migrate: (persistedState) => persistedState as UiState,
    },
  ),
)
