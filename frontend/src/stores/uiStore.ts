import { create } from 'zustand'

interface UIStore {
  // State
  sidebarOpen: boolean
  commandPaletteOpen: boolean
  settingsOpen: boolean
  splitViewEnabled: boolean
  secondarySessionId: string | null

  // Actions
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  toggleCommandPalette: () => void
  setCommandPaletteOpen: (open: boolean) => void
  toggleSettings: () => void
  setSettingsOpen: (open: boolean) => void
  toggleSplitView: () => void
  setSplitViewEnabled: (enabled: boolean) => void
  setSecondarySession: (id: string | null) => void
}

export const useUIStore = create<UIStore>((set) => ({
  // Initial state
  sidebarOpen: true,
  commandPaletteOpen: false,
  settingsOpen: false,
  splitViewEnabled: false,
  secondarySessionId: null,

  // Actions
  toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  toggleCommandPalette: () => set(state => ({ commandPaletteOpen: !state.commandPaletteOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  toggleSettings: () => set(state => ({ settingsOpen: !state.settingsOpen })),
  setSettingsOpen: (open) => set({ settingsOpen: open }),

  toggleSplitView: () => set(state => ({ splitViewEnabled: !state.splitViewEnabled })),
  setSplitViewEnabled: (enabled) => set({ splitViewEnabled: enabled }),

  setSecondarySession: (id) => set({ secondarySessionId: id }),
}))
