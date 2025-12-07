# Task: Sidebar & Session Management

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create SessionList with date grouping, SessionItem with context menu, SessionSearch, and useSessions hook
**Sequence**: 8 of 14
**Depends On**: 07-model-agent-selectors.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `0380be1d-6eab-4f76-a7a7-06ef7794614c`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/0380be1d-6eab-4f76-a7a7-06ef7794614c" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/0380be1d-6eab-4f76-a7a7-06ef7794614c" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The existing Sidebar.tsx is a basic implementation that needs enhancement with:

- **Session Grouping**: Group sessions by date (Today, Yesterday, Last 7 Days, Older)
- **Context Menu**: Right-click or dropdown menu for Rename, Open in Split, Delete
- **Search**: Filter sessions by title
- **Collapsible Groups**: Expandable date groups for better organization

We'll install date-fns for date manipulation and create modular sidebar components.

---

## Requirements

### 1. Install date-fns

```bash
cd /Users/maxwell/Projects/MAI/frontend
npm install date-fns
```

### 2. Create useSessions Hook

Create `frontend/src/hooks/useSessions.ts`:

```tsx
import { useState, useCallback, useMemo } from 'react'
import { useChatStore } from '@/stores'
import { isToday, isYesterday, isWithinInterval, subDays } from 'date-fns'
import type { ChatSession } from '@/types/chat'

interface UseSessionsReturn {
  sessions: ChatSession[]
  groupedSessions: GroupedSessions
  searchQuery: string
  setSearchQuery: (query: string) => void
  createSession: () => string
  deleteSession: (id: string) => void
  renameSession: (id: string, title: string) => void
}

export interface GroupedSessions {
  today: ChatSession[]
  yesterday: ChatSession[]
  lastWeek: ChatSession[]
  older: ChatSession[]
}

export function useSessions(): UseSessionsReturn {
  const [searchQuery, setSearchQuery] = useState('')

  const sessions = useChatStore(state => state.sessions)
  const createSession = useChatStore(state => state.createSession)
  const deleteSession = useChatStore(state => state.deleteSession)
  const renameSession = useChatStore(state => state.renameSession)

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions

    const query = searchQuery.toLowerCase()
    return sessions.filter(session =>
      session.title.toLowerCase().includes(query)
    )
  }, [sessions, searchQuery])

  const groupedSessions = useMemo(() => {
    const now = new Date()
    const weekAgo = subDays(now, 7)

    const groups: GroupedSessions = {
      today: [],
      yesterday: [],
      lastWeek: [],
      older: [],
    }

    // Sort by updatedAt descending
    const sorted = [...filteredSessions].sort(
      (a, b) => b.updatedAt - a.updatedAt
    )

    for (const session of sorted) {
      const sessionDate = new Date(session.updatedAt)

      if (isToday(sessionDate)) {
        groups.today.push(session)
      } else if (isYesterday(sessionDate)) {
        groups.yesterday.push(session)
      } else if (isWithinInterval(sessionDate, { start: weekAgo, end: now })) {
        groups.lastWeek.push(session)
      } else {
        groups.older.push(session)
      }
    }

    return groups
  }, [filteredSessions])

  return {
    sessions: filteredSessions,
    groupedSessions,
    searchQuery,
    setSearchQuery,
    createSession,
    deleteSession,
    renameSession,
  }
}
```

### 3. Create SessionSearch Component

Create `frontend/src/components/sidebar/SessionSearch.tsx`:

```tsx
import { Input } from '@/components/ui/input'
import { Search, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SessionSearchProps {
  value: string
  onChange: (value: string) => void
}

export function SessionSearch({ value, onChange }: SessionSearchProps) {
  return (
    <div className="px-3 pb-2">
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder="Search chats..."
          className="pl-8 pr-8 h-9"
        />
        {value && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1 h-7 w-7"
            onClick={() => onChange('')}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  )
}
```

### 4. Create SessionItem Component

Create `frontend/src/components/sidebar/SessionItem.tsx`:

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useChatStore, useUIStore } from '@/stores'
import { cn } from '@/lib/utils'
import {
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Columns,
  Trash,
} from 'lucide-react'
import type { ChatSession } from '@/types/chat'

interface SessionItemProps {
  session: ChatSession
  onDelete: (id: string) => void
  onRename: (id: string, title: string) => void
}

export function SessionItem({ session, onDelete, onRename }: SessionItemProps) {
  const [renameDialogOpen, setRenameDialogOpen] = useState(false)
  const [newTitle, setNewTitle] = useState(session.title)
  const navigate = useNavigate()

  const activeSessionId = useChatStore(state => state.activeSessionId)
  const setActiveSession = useChatStore(state => state.setActiveSession)
  const { toggleSplitView, setSecondarySession, splitViewEnabled } = useUIStore()

  const isActive = session.id === activeSessionId

  const handleClick = () => {
    setActiveSession(session.id)
    navigate(`/chat/${session.id}`)
  }

  const handleOpenInSplit = () => {
    if (!splitViewEnabled) {
      toggleSplitView()
    }
    setSecondarySession(session.id)
  }

  const handleRename = () => {
    if (newTitle.trim() && newTitle !== session.title) {
      onRename(session.id, newTitle.trim())
    }
    setRenameDialogOpen(false)
  }

  const handleDelete = () => {
    onDelete(session.id)
    // If deleting active session, navigate to home
    if (isActive) {
      navigate('/')
    }
  }

  return (
    <>
      <div
        className={cn(
          'group flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer transition-colors',
          isActive ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'
        )}
        onClick={handleClick}
      >
        <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="flex-1 truncate text-sm">{session.title}</span>

        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={e => e.stopPropagation()}>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                'h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity',
                isActive && 'opacity-100'
              )}
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => {
              setNewTitle(session.title)
              setRenameDialogOpen(true)
            }}>
              <Pencil className="mr-2 h-4 w-4" />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleOpenInSplit}>
              <Columns className="mr-2 h-4 w-4" />
              Open in Split View
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleDelete}
              className="text-destructive focus:text-destructive"
            >
              <Trash className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Chat</DialogTitle>
          </DialogHeader>
          <Input
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            placeholder="Chat title"
            onKeyDown={e => e.key === 'Enter' && handleRename()}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRename}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

### 5. Create SessionGroup Component

Create `frontend/src/components/sidebar/SessionGroup.tsx`:

```tsx
import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SessionItem } from './SessionItem'
import type { ChatSession } from '@/types/chat'

interface SessionGroupProps {
  title: string
  sessions: ChatSession[]
  defaultOpen?: boolean
  onDelete: (id: string) => void
  onRename: (id: string, title: string) => void
}

export function SessionGroup({
  title,
  sessions,
  defaultOpen = true,
  onDelete,
  onRename,
}: SessionGroupProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  if (sessions.length === 0) return null

  return (
    <div className="mb-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 px-2 py-1 text-xs text-muted-foreground hover:text-foreground w-full"
      >
        {isOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <span>{title}</span>
        <span className="ml-auto text-[10px]">{sessions.length}</span>
      </button>

      {isOpen && (
        <div className="space-y-0.5 mt-1">
          {sessions.map(session => (
            <SessionItem
              key={session.id}
              session={session}
              onDelete={onDelete}
              onRename={onRename}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

### 6. Create SessionList Component

Create `frontend/src/components/sidebar/SessionList.tsx`:

```tsx
import { SessionGroup } from './SessionGroup'
import type { GroupedSessions } from '@/hooks/useSessions'

interface SessionListProps {
  groupedSessions: GroupedSessions
  onDelete: (id: string) => void
  onRename: (id: string, title: string) => void
}

export function SessionList({
  groupedSessions,
  onDelete,
  onRename,
}: SessionListProps) {
  const hasNoSessions =
    groupedSessions.today.length === 0 &&
    groupedSessions.yesterday.length === 0 &&
    groupedSessions.lastWeek.length === 0 &&
    groupedSessions.older.length === 0

  if (hasNoSessions) {
    return (
      <div className="px-4 py-8 text-center text-sm text-muted-foreground">
        <p>No chats yet</p>
        <p className="text-xs mt-1">Create a new chat to get started</p>
      </div>
    )
  }

  return (
    <div className="px-2">
      <SessionGroup
        title="Today"
        sessions={groupedSessions.today}
        defaultOpen={true}
        onDelete={onDelete}
        onRename={onRename}
      />
      <SessionGroup
        title="Yesterday"
        sessions={groupedSessions.yesterday}
        defaultOpen={true}
        onDelete={onDelete}
        onRename={onRename}
      />
      <SessionGroup
        title="Last 7 Days"
        sessions={groupedSessions.lastWeek}
        defaultOpen={true}
        onDelete={onDelete}
        onRename={onRename}
      />
      <SessionGroup
        title="Older"
        sessions={groupedSessions.older}
        defaultOpen={false}
        onDelete={onDelete}
        onRename={onRename}
      />
    </div>
  )
}
```

### 7. Create Sidebar Components Index

Create `frontend/src/components/sidebar/index.ts`:

```tsx
export { SessionSearch } from './SessionSearch'
export { SessionItem } from './SessionItem'
export { SessionGroup } from './SessionGroup'
export { SessionList } from './SessionList'
export { Sidebar } from './Sidebar'
```

### 8. Create Enhanced Sidebar Component

Create `frontend/src/components/sidebar/Sidebar.tsx`:

```tsx
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { SessionSearch } from './SessionSearch'
import { SessionList } from './SessionList'
import { useSessions } from '@/hooks/useSessions'
import { useUIStore } from '@/stores'
import { cn } from '@/lib/utils'
import { Plus, BarChart3, Settings, X } from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
}

export function Sidebar({ isOpen }: SidebarProps) {
  const navigate = useNavigate()
  const { toggleSidebar } = useUIStore()
  const {
    groupedSessions,
    searchQuery,
    setSearchQuery,
    createSession,
    deleteSession,
    renameSession,
  } = useSessions()

  const handleNewChat = () => {
    const newId = createSession()
    navigate(`/chat/${newId}`)
  }

  return (
    <aside
      className={cn(
        'w-64 border-r border-border flex flex-col bg-background transition-all duration-300',
        !isOpen && 'w-0 overflow-hidden border-r-0'
      )}
    >
      {/* Header */}
      <div className="h-14 px-3 flex items-center justify-between border-b border-border">
        <span className="font-semibold text-lg">MAI</span>
        <Button variant="ghost" size="icon" onClick={toggleSidebar}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <Button className="w-full" onClick={handleNewChat}>
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Search */}
      <SessionSearch value={searchQuery} onChange={setSearchQuery} />

      {/* Session List */}
      <ScrollArea className="flex-1">
        <SessionList
          groupedSessions={groupedSessions}
          onDelete={deleteSession}
          onRename={renameSession}
        />
      </ScrollArea>

      {/* Bottom Navigation */}
      <Separator />
      <div className="p-2 space-y-1">
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={() => navigate('/analytics')}
        >
          <BarChart3 className="mr-2 h-4 w-4" />
          Analytics
        </Button>
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={() => navigate('/settings')}
        >
          <Settings className="mr-2 h-4 w-4" />
          Settings
        </Button>
      </div>
    </aside>
  )
}
```

### 9. Update Hooks Index

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
```

### 10. Update MainLayout to Use New Sidebar

Update `frontend/src/components/layout/MainLayout.tsx`:

```tsx
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from '@/components/sidebar'
import { useUIStore } from '@/stores'

export function MainLayout() {
  const { sidebarOpen } = useUIStore()

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
    </div>
  )
}
```

---

## Files to Create

- `frontend/src/hooks/useSessions.ts` - Sessions management hook
- `frontend/src/components/sidebar/SessionSearch.tsx` - Search input
- `frontend/src/components/sidebar/SessionItem.tsx` - Individual session row
- `frontend/src/components/sidebar/SessionGroup.tsx` - Collapsible date group
- `frontend/src/components/sidebar/SessionList.tsx` - Grouped session list
- `frontend/src/components/sidebar/Sidebar.tsx` - Complete sidebar
- `frontend/src/components/sidebar/index.ts` - Exports

## Files to Modify

- `frontend/src/hooks/index.ts` - Export useSessions
- `frontend/src/components/layout/MainLayout.tsx` - Use new Sidebar
- `frontend/package.json` - Add date-fns (via npm install)

---

## Success Criteria

```bash
# Verify date-fns installed
cd /Users/maxwell/Projects/MAI/frontend
cat package.json | grep "date-fns"
# Expected: "date-fns": "^x.x.x"

# Verify sidebar components
ls /Users/maxwell/Projects/MAI/frontend/src/components/sidebar/
# Expected: SessionSearch.tsx, SessionItem.tsx, SessionGroup.tsx, SessionList.tsx, Sidebar.tsx, index.ts

# Verify TypeScript compiles
npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts
```

**Checklist:**
- [ ] date-fns installed
- [ ] Sessions grouped by Today, Yesterday, Last 7 Days, Older
- [ ] Groups are collapsible with count badges
- [ ] Search filters sessions by title
- [ ] Context menu has Rename, Open in Split, Delete
- [ ] Rename opens dialog with input
- [ ] Delete removes session and navigates if active
- [ ] Open in Split enables split view
- [ ] New Chat button creates session and navigates
- [ ] Bottom nav links to Analytics and Settings

---

## Technical Notes

- **date-fns**: Lightweight date utilities (isToday, isYesterday, etc.)
- **Grouping**: Sessions sorted by updatedAt within each group
- **Search**: Case-insensitive title matching
- **Navigation**: Uses React Router's navigate for route changes
- **Delete Handling**: Navigates away if deleting active session

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 09-settings-panel.md
