import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LLMProvider } from '@/types/chat'

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

  // New provider settings
  llmProvider: LLMProvider
  ollamaUrl: string
  llamacppUrl: string
  mlxUrl: string
  openaiApiKey: string

  // Actions
  setTheme: (theme: Theme) => void
  toggleVimMode: () => void
  setVimMode: (enabled: boolean) => void
  setFontSize: (size: number) => void
  setApiBaseUrl: (url: string) => void
  setLMStudioUrl: (url: string) => void
  updateShortcut: (action: keyof KeyboardShortcuts, keys: string) => void
  resetToDefaults: () => void

  // New provider actions
  setLLMProvider: (provider: LLMProvider) => void
  setOllamaUrl: (url: string) => void
  setLlamaCppUrl: (url: string) => void
  setMLXUrl: (url: string) => void
  setOpenAIApiKey: (key: string) => void
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
  // New provider defaults
  llmProvider: 'auto' as LLMProvider,
  ollamaUrl: 'http://localhost:11434',
  llamacppUrl: 'http://localhost:8080',
  mlxUrl: 'http://localhost:8081',
  openaiApiKey: '',
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

      // New provider actions
      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setOllamaUrl: (url) => set({ ollamaUrl: url }),
      setLlamaCppUrl: (url) => set({ llamacppUrl: url }),
      setMLXUrl: (url) => set({ mlxUrl: url }),
      setOpenAIApiKey: (key) => set({ openaiApiKey: key }),
    }),
    {
      name: 'mai-settings-storage',
      version: 1,
      migrate: (persistedState: unknown, version: number) => {
        const state = persistedState as Partial<SettingsStore>
        if (version === 0) {
          // Migration from version 0: Add missing provider fields
          return {
            ...DEFAULT_SETTINGS,
            ...state,
            llmProvider: state.llmProvider || DEFAULT_SETTINGS.llmProvider,
            ollamaUrl: state.ollamaUrl || DEFAULT_SETTINGS.ollamaUrl,
            llamacppUrl: state.llamacppUrl || DEFAULT_SETTINGS.llamacppUrl,
            mlxUrl: state.mlxUrl || DEFAULT_SETTINGS.mlxUrl,
            openaiApiKey: state.openaiApiKey || DEFAULT_SETTINGS.openaiApiKey,
          }
        }
        return state as SettingsStore
      },
    }
  )
)
