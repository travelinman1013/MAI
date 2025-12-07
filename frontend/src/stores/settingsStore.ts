import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

interface KeyboardShortcuts {
  newChat: string
  commandPalette: string
  toggleSidebar: string
  focusInput: string
  sendMessage: string
  toggleSplitView: string
  toggleSettings: string
}

interface SettingsStore {
  // State
  theme: Theme
  vimMode: boolean
  fontSize: number
  apiBaseUrl: string
  lmStudioUrl: string
  keyboardShortcuts: KeyboardShortcuts

  // Actions
  setTheme: (theme: Theme) => void
  toggleVimMode: () => void
  setVimMode: (enabled: boolean) => void
  setFontSize: (size: number) => void
  setApiBaseUrl: (url: string) => void
  setLMStudioUrl: (url: string) => void
  updateShortcut: (action: keyof KeyboardShortcuts, keys: string) => void
  resetToDefaults: () => void
}

const DEFAULT_SHORTCUTS: KeyboardShortcuts = {
  newChat: 'Ctrl+N',
  commandPalette: 'Cmd+K',
  toggleSidebar: 'Cmd+B',
  focusInput: '/',
  sendMessage: 'Enter',
  toggleSplitView: 'Cmd+\\',
  toggleSettings: 'Cmd+,',
}

const DEFAULT_SETTINGS = {
  theme: 'dark' as Theme,
  vimMode: false,
  fontSize: 14,
  apiBaseUrl: '/api/v1',
  lmStudioUrl: 'http://localhost:1234',
  keyboardShortcuts: DEFAULT_SHORTCUTS,
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,

      setTheme: (theme) => {
        set({ theme })
        // Apply theme to document
        const root = document.documentElement
        root.classList.remove('light', 'dark')
        if (theme === 'system') {
          const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
          root.classList.add(systemTheme)
        } else {
          root.classList.add(theme)
        }
      },

      toggleVimMode: () => set(state => ({ vimMode: !state.vimMode })),
      setVimMode: (enabled) => set({ vimMode: enabled }),

      setFontSize: (size) => set({ fontSize: size }),
      setApiBaseUrl: (url) => set({ apiBaseUrl: url }),
      setLMStudioUrl: (url) => set({ lmStudioUrl: url }),

      updateShortcut: (action, keys) => {
        set(state => ({
          keyboardShortcuts: {
            ...state.keyboardShortcuts,
            [action]: keys,
          },
        }))
      },

      resetToDefaults: () => set(DEFAULT_SETTINGS),
    }),
    {
      name: 'mai-settings-storage',
    }
  )
)
