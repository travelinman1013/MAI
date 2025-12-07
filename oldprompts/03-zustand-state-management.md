# Task: Zustand State Management Setup

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Install Zustand and create chatStore, uiStore, and settingsStore
**Sequence**: 3 of 14
**Depends On**: 02-core-ui-components.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `db71a383-8110-4ff5-a9fc-8cd5a0f1f974`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/db71a383-8110-4ff5-a9fc-8cd5a0f1f974" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/db71a383-8110-4ff5-a9fc-8cd5a0f1f974" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With UI components ready, we need global state management. The current App.tsx uses local useState, but we need shared state across:
- Chat sessions and messages (chatStore)
- UI state like sidebar/dialogs (uiStore)
- User preferences (settingsStore)

Zustand is a minimal, TypeScript-friendly state manager that works well with React 18.

---

## Requirements

### 1. Install Zustand

```bash
cd /Users/maxwell/Projects/MAI/frontend
npm install zustand
```

### 2. Create Chat Store

Create `frontend/src/stores/chatStore.ts`:

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  images?: string[]
  isStreaming?: boolean
}

export interface ChatSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  agentName: string
  modelId: string | null
}

interface ChatStore {
  // State
  sessions: ChatSession[]
  activeSessionId: string | null
  messages: Record<string, Message[]>
  isStreaming: boolean
  activeAgent: string
  activeModel: string | null

  // Actions
  createSession: () => string
  deleteSession: (id: string) => void
  renameSession: (id: string, title: string) => void
  setActiveSession: (id: string | null) => void
  addMessage: (sessionId: string, message: Message) => void
  updateMessage: (sessionId: string, messageId: string, content: string) => void
  clearMessages: (sessionId: string) => void
  setStreaming: (isStreaming: boolean) => void
  setAgent: (agentName: string) => void
  setModel: (modelId: string | null) => void
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      // Initial state
      sessions: [],
      activeSessionId: null,
      messages: {},
      isStreaming: false,
      activeAgent: 'chat',
      activeModel: null,

      // Actions
      createSession: () => {
        const id = crypto.randomUUID()
        const session: ChatSession = {
          id,
          title: 'New Chat',
          createdAt: new Date(),
          updatedAt: new Date(),
          agentName: get().activeAgent,
          modelId: get().activeModel,
        }
        set(state => ({
          sessions: [session, ...state.sessions],
          activeSessionId: id,
          messages: { ...state.messages, [id]: [] },
        }))
        return id
      },

      deleteSession: (id) => {
        set(state => {
          const { [id]: _, ...remainingMessages } = state.messages
          const sessions = state.sessions.filter(s => s.id !== id)
          return {
            sessions,
            messages: remainingMessages,
            activeSessionId: state.activeSessionId === id
              ? sessions[0]?.id ?? null
              : state.activeSessionId,
          }
        })
      },

      renameSession: (id, title) => {
        set(state => ({
          sessions: state.sessions.map(s =>
            s.id === id ? { ...s, title, updatedAt: new Date() } : s
          ),
        }))
      },

      setActiveSession: (id) => {
        set({ activeSessionId: id })
      },

      addMessage: (sessionId, message) => {
        set(state => ({
          messages: {
            ...state.messages,
            [sessionId]: [...(state.messages[sessionId] || []), message],
          },
          sessions: state.sessions.map(s =>
            s.id === sessionId ? { ...s, updatedAt: new Date() } : s
          ),
        }))
      },

      updateMessage: (sessionId, messageId, content) => {
        set(state => ({
          messages: {
            ...state.messages,
            [sessionId]: (state.messages[sessionId] || []).map(m =>
              m.id === messageId ? { ...m, content } : m
            ),
          },
        }))
      },

      clearMessages: (sessionId) => {
        set(state => ({
          messages: { ...state.messages, [sessionId]: [] },
        }))
      },

      setStreaming: (isStreaming) => set({ isStreaming }),
      setAgent: (agentName) => set({ activeAgent: agentName }),
      setModel: (modelId) => set({ activeModel: modelId }),
    }),
    {
      name: 'mai-chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        messages: state.messages,
        activeSessionId: state.activeSessionId,
        activeAgent: state.activeAgent,
        activeModel: state.activeModel,
      }),
    }
  )
)
```

### 3. Create UI Store

Create `frontend/src/stores/uiStore.ts`:

```typescript
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
```

### 4. Create Settings Store

Create `frontend/src/stores/settingsStore.ts`:

```typescript
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
```

### 5. Create Store Index

Create `frontend/src/stores/index.ts`:

```typescript
export { useChatStore } from './chatStore'
export type { Message, ChatSession } from './chatStore'

export { useUIStore } from './uiStore'

export { useSettingsStore } from './settingsStore'
```

### 6. Update Types

Update `frontend/src/types/chat.ts` to re-export store types:

```typescript
// Re-export from stores for backwards compatibility
export type { Message, ChatSession } from '@/stores/chatStore'

export interface Model {
  id: string
  name: string
  provider?: string
}

export interface AgentInfo {
  name: string
  description: string
  capabilities?: string[]
}

export interface LLMStatus {
  connected: boolean
  model: string | null
}
```

---

## Files to Create

- `frontend/src/stores/chatStore.ts`
- `frontend/src/stores/uiStore.ts`
- `frontend/src/stores/settingsStore.ts`
- `frontend/src/stores/index.ts`

## Files to Modify

- `frontend/src/types/chat.ts` - Update to use store types

---

## Success Criteria

```bash
# Verify zustand installed
grep "zustand" /Users/maxwell/Projects/MAI/frontend/package.json
# Expected: "zustand": "^4.x.x" or "^5.x.x"

# Verify store files exist
ls /Users/maxwell/Projects/MAI/frontend/src/stores/
# Expected: chatStore.ts, uiStore.ts, settingsStore.ts, index.ts

# Verify TypeScript compiles
cd /Users/maxwell/Projects/MAI/frontend && npm run build 2>&1 | grep -i error
# Expected: No errors
```

**Checklist:**
- [ ] Zustand installed
- [ ] chatStore with sessions, messages, streaming state
- [ ] uiStore with sidebar, dialogs, split view state
- [ ] settingsStore with theme, vim mode, shortcuts (persisted)
- [ ] TypeScript compiles without errors

---

## Technical Notes

- **Persistence**: chatStore and settingsStore use zustand/persist middleware
- **localStorage Keys**: `mai-chat-storage` and `mai-settings-storage`
- **Theme Application**: settingsStore.setTheme() also updates document.documentElement class
- **Session Creation**: createSession() returns the new session ID for navigation

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 04-layout-routing.md
