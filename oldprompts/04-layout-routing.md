# Task: Layout Components & React Router Setup

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create MainLayout, Header, providers, and configure React Router
**Sequence**: 4 of 14
**Depends On**: 03-zustand-state-management.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `1cc3127d-8727-4e30-81c1-7a7cdc7220ba`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/1cc3127d-8727-4e30-81c1-7a7cdc7220ba" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/1cc3127d-8727-4e30-81c1-7a7cdc7220ba" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With Zustand stores ready, we now create the application shell:
- MainLayout wrapping all pages with sidebar and header
- Header with model selector, theme toggle, command palette button
- React Router for navigation between chat, analytics, and settings
- Provider wrapper for any future context needs

The existing App.tsx will be refactored to use the router.

---

## Requirements

### 1. Create Providers Wrapper

Create `frontend/src/app/providers.tsx`:

```tsx
import { ReactNode, useEffect } from 'react'
import { useSettingsStore } from '@/stores'

interface ProvidersProps {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  const { theme } = useSettingsStore()

  // Apply theme on mount and when it changes
  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('light', 'dark')

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      root.classList.add(systemTheme)
    } else {
      root.classList.add(theme)
    }
  }, [theme])

  return <>{children}</>
}
```

### 2. Create Header Component

Create `frontend/src/components/layout/Header.tsx`:

```tsx
import { PanelLeft, Command, Sun, Moon, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useUIStore, useSettingsStore } from '@/stores'

export function Header() {
  const { toggleSidebar, toggleCommandPalette, toggleSettings } = useUIStore()
  const { theme, setTheme } = useSettingsStore()

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <header className="h-14 border-b border-border flex items-center px-4 gap-2 bg-background">
      {/* Sidebar Toggle */}
      <Button variant="ghost" size="icon" onClick={toggleSidebar}>
        <PanelLeft className="h-5 w-5" />
      </Button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Command Palette Button */}
      <Button
        variant="outline"
        size="sm"
        className="gap-2 text-muted-foreground"
        onClick={toggleCommandPalette}
      >
        <Command className="h-4 w-4" />
        <span className="hidden sm:inline">Command</span>
        <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>

      {/* Theme Toggle */}
      <Button variant="ghost" size="icon" onClick={toggleTheme}>
        {theme === 'dark' ? (
          <Sun className="h-5 w-5" />
        ) : (
          <Moon className="h-5 w-5" />
        )}
      </Button>

      {/* Settings */}
      <Button variant="ghost" size="icon" onClick={toggleSettings}>
        <Settings className="h-5 w-5" />
      </Button>
    </header>
  )
}
```

### 3. Create MainLayout Component

Create `frontend/src/components/layout/MainLayout.tsx`:

```tsx
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import Sidebar from '@/components/Sidebar'
import { useUIStore } from '@/stores'

export function MainLayout() {
  const { sidebarOpen } = useUIStore()

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onToggle={() => {}} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* Dialogs rendered here later: CommandPalette, SettingsDialog */}
    </div>
  )
}
```

### 4. Create Chat Page

Create `frontend/src/pages/ChatPage.tsx`:

```tsx
import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Chat from '@/components/Chat'
import { useChatStore } from '@/stores'

export function ChatPage() {
  const { sessionId } = useParams<{ sessionId?: string }>()
  const navigate = useNavigate()
  const {
    sessions,
    activeSessionId,
    setActiveSession,
    createSession
  } = useChatStore()

  useEffect(() => {
    // If URL has sessionId, set it as active
    if (sessionId) {
      const exists = sessions.some(s => s.id === sessionId)
      if (exists) {
        setActiveSession(sessionId)
      } else {
        // Session doesn't exist, redirect to home
        navigate('/', { replace: true })
      }
    } else if (!activeSessionId && sessions.length === 0) {
      // No sessions exist, create one
      const newId = createSession()
      navigate(`/chat/${newId}`, { replace: true })
    } else if (activeSessionId) {
      // Have active session but URL doesn't match, update URL
      navigate(`/chat/${activeSessionId}`, { replace: true })
    } else if (sessions.length > 0) {
      // Have sessions but none active, activate first
      setActiveSession(sessions[0].id)
      navigate(`/chat/${sessions[0].id}`, { replace: true })
    }
  }, [sessionId, activeSessionId, sessions, setActiveSession, createSession, navigate])

  return <Chat />
}
```

### 5. Create Analytics Page (Placeholder)

Create `frontend/src/pages/AnalyticsPage.tsx`:

```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { BarChart3 } from 'lucide-react'

export function AnalyticsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Coming Soon
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Analytics dashboard will be implemented in a later step.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 6. Create Settings Page (Placeholder)

Create `frontend/src/pages/SettingsPage.tsx`:

```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Settings } from 'lucide-react'

export function SettingsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Coming Soon
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Settings panel will be implemented in a later step.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 7. Create Routes Configuration

Create `frontend/src/app/routes.tsx`:

```tsx
import { createBrowserRouter } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { ChatPage } from '@/pages/ChatPage'
import { AnalyticsPage } from '@/pages/AnalyticsPage'
import { SettingsPage } from '@/pages/SettingsPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <ChatPage /> },
      { path: 'chat/:sessionId', element: <ChatPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
])
```

### 8. Create Pages Index

Create `frontend/src/pages/index.ts`:

```tsx
export { ChatPage } from './ChatPage'
export { AnalyticsPage } from './AnalyticsPage'
export { SettingsPage } from './SettingsPage'
```

### 9. Update App.tsx

Replace `frontend/src/App.tsx`:

```tsx
import { RouterProvider } from 'react-router-dom'
import { Providers } from './app/providers'
import { router } from './app/routes'

function App() {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  )
}

export default App
```

### 10. Create Directory Structure

```bash
mkdir -p frontend/src/app
mkdir -p frontend/src/pages
mkdir -p frontend/src/components/layout
```

---

## Files to Create

- `frontend/src/app/providers.tsx`
- `frontend/src/app/routes.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/components/layout/MainLayout.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/pages/AnalyticsPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/index.ts`

## Files to Modify

- `frontend/src/App.tsx` - Replace with router setup

---

## Success Criteria

```bash
# Verify new directories exist
ls /Users/maxwell/Projects/MAI/frontend/src/app/
# Expected: providers.tsx, routes.tsx

ls /Users/maxwell/Projects/MAI/frontend/src/pages/
# Expected: ChatPage.tsx, AnalyticsPage.tsx, SettingsPage.tsx, index.ts

# Verify TypeScript compiles
cd /Users/maxwell/Projects/MAI/frontend && npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
cd /Users/maxwell/Projects/MAI/frontend && timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts on localhost:5173
```

**Checklist:**
- [ ] MainLayout renders sidebar and header
- [ ] Header has sidebar toggle, command palette button, theme toggle, settings button
- [ ] React Router configured with routes for /, /chat/:sessionId, /analytics, /settings
- [ ] ChatPage syncs URL with activeSessionId
- [ ] Theme toggle works (switches between light/dark)

---

## Technical Notes

- **Outlet**: React Router's Outlet renders child routes inside MainLayout
- **URL Sync**: ChatPage keeps URL in sync with active session ID
- **Existing Sidebar**: Uses current Sidebar component (will be enhanced later)
- **Existing Chat**: Uses current Chat component (will be enhanced later)

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 05-chat-components.md
