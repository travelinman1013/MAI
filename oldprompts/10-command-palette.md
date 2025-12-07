# Task: Command Palette with cmdk

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Install cmdk, create CommandPalette with actions, theme switching, session search, and Cmd+K shortcut
**Sequence**: 10 of 14
**Depends On**: 09-settings-panel.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `6f0dd940-9129-4180-ad4f-b1f856f91dc7`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/6f0dd940-9129-4180-ad4f-b1f856f91dc7" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/6f0dd940-9129-4180-ad4f-b1f856f91dc7" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The command palette is a power-user feature that provides quick access to all app functionality via keyboard. Using the cmdk library (from the creator of Vercel), we'll create a searchable command menu that:

- Opens with Cmd+K (or Ctrl+K on Windows/Linux)
- Provides quick actions (New Chat, Settings, Analytics)
- Allows theme switching
- Shows recent chats for quick navigation
- Searches across all actions and sessions

This is a key UX improvement that makes the app feel professional and efficient.

---

## Requirements

### 1. Install cmdk

```bash
cd /Users/maxwell/Projects/MAI/frontend
npm install cmdk
```

### 2. Create CommandPalette Component

Create `frontend/src/components/command/CommandPalette.tsx`:

```tsx
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Command } from 'cmdk'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useChatStore, useUIStore, useSettingsStore } from '@/stores'
import { useSessions } from '@/hooks/useSessions'
import {
  Plus,
  MessageSquare,
  BarChart3,
  Settings,
  Sun,
  Moon,
  Monitor,
  Keyboard,
  PanelLeft,
  Columns,
  Search,
} from 'lucide-react'

export function CommandPalette() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const { commandPaletteOpen, toggleCommandPalette, toggleSidebar, toggleSplitView, toggleSettings } = useUIStore()
  const { theme, setTheme } = useSettingsStore()
  const { sessions, createSession } = useSessions()
  const setActiveSession = useChatStore(state => state.setActiveSession)

  // Keyboard shortcut to open
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        toggleCommandPalette()
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [toggleCommandPalette])

  const runCommand = useCallback((command: () => void) => {
    toggleCommandPalette()
    command()
  }, [toggleCommandPalette])

  const handleNewChat = () => {
    const newId = createSession()
    navigate(`/chat/${newId}`)
  }

  const handleOpenSession = (sessionId: string) => {
    setActiveSession(sessionId)
    navigate(`/chat/${sessionId}`)
  }

  // Reset search when closing
  useEffect(() => {
    if (!commandPaletteOpen) {
      setSearch('')
    }
  }, [commandPaletteOpen])

  return (
    <Dialog open={commandPaletteOpen} onOpenChange={toggleCommandPalette}>
      <DialogContent className="p-0 max-w-lg overflow-hidden">
        <Command className="rounded-lg border-0 shadow-none" loop>
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Type a command or search..."
              className="flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
          <Command.List className="max-h-[400px] overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>

            {/* Actions Group */}
            <Command.Group heading="Actions">
              <CommandItem
                icon={Plus}
                onSelect={() => runCommand(handleNewChat)}
              >
                New Chat
              </CommandItem>
              <CommandItem
                icon={BarChart3}
                onSelect={() => runCommand(() => navigate('/analytics'))}
              >
                Analytics Dashboard
              </CommandItem>
              <CommandItem
                icon={Settings}
                onSelect={() => runCommand(toggleSettings)}
              >
                Settings
              </CommandItem>
              <CommandItem
                icon={PanelLeft}
                onSelect={() => runCommand(toggleSidebar)}
              >
                Toggle Sidebar
              </CommandItem>
              <CommandItem
                icon={Columns}
                onSelect={() => runCommand(toggleSplitView)}
              >
                Toggle Split View
              </CommandItem>
            </Command.Group>

            {/* Theme Group */}
            <Command.Group heading="Theme">
              <CommandItem
                icon={Sun}
                onSelect={() => runCommand(() => setTheme('light'))}
              >
                Light Mode
                {theme === 'light' && <span className="ml-auto text-xs text-primary">Active</span>}
              </CommandItem>
              <CommandItem
                icon={Moon}
                onSelect={() => runCommand(() => setTheme('dark'))}
              >
                Dark Mode
                {theme === 'dark' && <span className="ml-auto text-xs text-primary">Active</span>}
              </CommandItem>
              <CommandItem
                icon={Monitor}
                onSelect={() => runCommand(() => setTheme('system'))}
              >
                System Theme
                {theme === 'system' && <span className="ml-auto text-xs text-primary">Active</span>}
              </CommandItem>
            </Command.Group>

            {/* Recent Chats Group */}
            {sessions.length > 0 && (
              <Command.Group heading="Recent Chats">
                {sessions.slice(0, 5).map(session => (
                  <CommandItem
                    key={session.id}
                    icon={MessageSquare}
                    onSelect={() => runCommand(() => handleOpenSession(session.id))}
                  >
                    {session.title}
                  </CommandItem>
                ))}
              </Command.Group>
            )}

            {/* Keyboard Shortcuts */}
            <Command.Group heading="Keyboard Shortcuts">
              <div className="px-2 py-3 text-xs text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>New Chat</span>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">⌘N</kbd>
                </div>
                <div className="flex justify-between">
                  <span>Toggle Sidebar</span>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">⌘B</kbd>
                </div>
                <div className="flex justify-between">
                  <span>Settings</span>
                  <kbd className="px-1.5 py-0.5 bg-muted rounded">⌘,</kbd>
                </div>
              </div>
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  )
}

// Helper component for command items
interface CommandItemProps {
  icon: React.ComponentType<{ className?: string }>
  onSelect: () => void
  children: React.ReactNode
}

function CommandItem({ icon: Icon, onSelect, children }: CommandItemProps) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex items-center gap-2 px-2 py-2 text-sm rounded-md cursor-pointer aria-selected:bg-accent aria-selected:text-accent-foreground"
    >
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="flex-1">{children}</span>
    </Command.Item>
  )
}
```

### 3. Create Command Components Index

Create `frontend/src/components/command/index.ts`:

```tsx
export { CommandPalette } from './CommandPalette'
```

### 4. Create useKeyboardShortcuts Hook

Create `frontend/src/hooks/useKeyboardShortcuts.ts`:

```tsx
import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUIStore, useSettingsStore, useChatStore } from '@/stores'

export function useKeyboardShortcuts() {
  const navigate = useNavigate()
  const { toggleSidebar, toggleCommandPalette, toggleSettings, toggleSplitView } = useUIStore()
  const { keyboardShortcuts, vimMode } = useSettingsStore()
  const createSession = useChatStore(state => state.createSession)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in inputs
    const target = e.target as HTMLElement
    const isInput = target.tagName === 'INPUT' ||
                    target.tagName === 'TEXTAREA' ||
                    target.isContentEditable

    // Build key string
    const parts: string[] = []
    if (e.metaKey) parts.push('⌘')
    if (e.ctrlKey && !e.metaKey) parts.push('Ctrl')
    if (e.altKey) parts.push('Alt')
    if (e.shiftKey) parts.push('Shift')

    const key = e.key.length === 1 ? e.key.toUpperCase() : e.key
    parts.push(key)
    const keyCombo = parts.join('')

    // Check against stored shortcuts
    const actions: Record<string, () => void> = {
      newChat: () => {
        const newId = createSession()
        navigate(`/chat/${newId}`)
      },
      commandPalette: toggleCommandPalette,
      toggleSidebar: toggleSidebar,
      toggleSplitView: toggleSplitView,
      toggleSettings: toggleSettings,
    }

    for (const [action, shortcut] of Object.entries(keyboardShortcuts)) {
      if (keyCombo === shortcut && actions[action]) {
        // Allow command palette shortcut even in inputs
        if (action === 'commandPalette' || !isInput) {
          e.preventDefault()
          actions[action]()
          return
        }
      }
    }

    // Vim mode shortcuts (only when not in input)
    if (vimMode && !isInput) {
      handleVimShortcut(e)
    }
  }, [keyboardShortcuts, vimMode, navigate, createSession, toggleCommandPalette, toggleSidebar, toggleSplitView, toggleSettings])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

function handleVimShortcut(e: KeyboardEvent) {
  switch (e.key) {
    case 'j':
      // Navigate to next session
      console.log('Vim: navigate down')
      break
    case 'k':
      // Navigate to previous session
      console.log('Vim: navigate up')
      break
    case 'i':
      // Focus input
      const input = document.querySelector('textarea') as HTMLTextAreaElement
      if (input) {
        input.focus()
      }
      break
    case '/':
      // Focus search
      const search = document.querySelector('[placeholder*="Search"]') as HTMLInputElement
      if (search) {
        e.preventDefault()
        search.focus()
      }
      break
  }
}
```

### 5. Update Hooks Index

Update `frontend/src/hooks/index.ts`:

```tsx
export { useModels } from './useModels'
export type { Model } from './useModels'
export { useAgents } from './useAgents'
export type { Agent } from './useAgents'
export { useLLMStatus } from './useLLMStatus'
export type { LLMStatus } from './useLLMStatus'
export { useSessions } from './useSessions'
export type { GroupedSessions } from './useSessions'
export { useKeyboardShortcuts } from './useKeyboardShortcuts'
```

### 6. Update MainLayout to Include CommandPalette and Keyboard Shortcuts

Update `frontend/src/components/layout/MainLayout.tsx`:

```tsx
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from '@/components/sidebar'
import { SettingsDialog } from '@/components/settings'
import { CommandPalette } from '@/components/command'
import { useUIStore } from '@/stores'
import { useKeyboardShortcuts } from '@/hooks'

export function MainLayout() {
  const { sidebarOpen } = useUIStore()

  // Initialize global keyboard shortcuts
  useKeyboardShortcuts()

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* Dialogs */}
      <SettingsDialog />
      <CommandPalette />
    </div>
  )
}
```

### 7. Create Directory Structure

```bash
mkdir -p frontend/src/components/command
```

---

## Files to Create

- `frontend/src/components/command/CommandPalette.tsx` - Command palette dialog
- `frontend/src/components/command/index.ts` - Exports
- `frontend/src/hooks/useKeyboardShortcuts.ts` - Global keyboard shortcuts

## Files to Modify

- `frontend/src/hooks/index.ts` - Export useKeyboardShortcuts
- `frontend/src/components/layout/MainLayout.tsx` - Add CommandPalette and useKeyboardShortcuts
- `frontend/package.json` - Add cmdk (via npm install)

---

## Success Criteria

```bash
# Verify cmdk installed
cd /Users/maxwell/Projects/MAI/frontend
cat package.json | grep "cmdk"
# Expected: "cmdk": "^x.x.x"

# Verify command components
ls /Users/maxwell/Projects/MAI/frontend/src/components/command/
# Expected: CommandPalette.tsx, index.ts

# Verify TypeScript compiles
npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts
```

**Checklist:**
- [ ] cmdk installed
- [ ] Command palette opens with Cmd+K (or Ctrl+K)
- [ ] Search filters commands and sessions
- [ ] "New Chat" action creates session and navigates
- [ ] "Analytics Dashboard" navigates to /analytics
- [ ] "Settings" opens settings dialog
- [ ] Theme switching works from command palette
- [ ] Recent chats show last 5 sessions
- [ ] Clicking a session navigates to it
- [ ] Escape closes the palette
- [ ] Global keyboard shortcuts work (⌘B for sidebar, etc.)

---

## Technical Notes

- **cmdk**: Headless command palette component with fuzzy search
- **Dialog Wrapper**: Uses shadcn Dialog for modal behavior
- **Loop Mode**: cmdk loop enables wrapping navigation with arrows
- **Command Styling**: Uses Tailwind's aria-selected for highlight state
- **Keyboard Shortcuts Hook**: Runs globally in MainLayout

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 11-analytics-dashboard.md
