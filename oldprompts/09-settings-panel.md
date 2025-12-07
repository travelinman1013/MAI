# Task: Settings Panel with Tabs

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create SettingsDialog with tabs for API, Models, Theme, and Keyboard settings
**Sequence**: 9 of 14
**Depends On**: 08-sidebar-sessions.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `b06c8c6d-80bf-429f-ad88-cc09b90c1e1c`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/b06c8c6d-80bf-429f-ad88-cc09b90c1e1c" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/b06c8c6d-80bf-429f-ad88-cc09b90c1e1c" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the core chat interface and sidebar complete, users need a centralized settings panel to configure:

- **API Settings**: Base URL, LM Studio URL
- **Model Settings**: View/manage available models
- **Theme Settings**: Light/dark/system theme, font size
- **Keyboard Settings**: Customize shortcuts, vim mode toggle

The settings dialog opens from the header settings button and stores preferences in the settingsStore with localStorage persistence.

---

## Requirements

### 1. Create APISettings Component

Create `frontend/src/components/settings/APISettings.tsx`:

```tsx
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useSettingsStore } from '@/stores'
import { useLLMStatus } from '@/hooks'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Check, X } from 'lucide-react'

export function APISettings() {
  const { apiBaseUrl, lmStudioUrl, setApiBaseUrl, setLMStudioUrl } = useSettingsStore()
  const { status, refresh, isLoading } = useLLMStatus()

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="apiBaseUrl">API Base URL</Label>
        <p className="text-sm text-muted-foreground">
          Backend API endpoint for MAI services
        </p>
        <Input
          id="apiBaseUrl"
          value={apiBaseUrl}
          onChange={e => setApiBaseUrl(e.target.value)}
          placeholder="http://localhost:8000"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="lmStudioUrl">LM Studio URL</Label>
        <p className="text-sm text-muted-foreground">
          Local LLM server endpoint
        </p>
        <div className="flex gap-2">
          <Input
            id="lmStudioUrl"
            value={lmStudioUrl}
            onChange={e => setLMStudioUrl(e.target.value)}
            placeholder="http://localhost:1234"
            className="flex-1"
          />
          <Button variant="outline" size="icon" onClick={refresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Connection Status */}
        <div className="flex items-center gap-2 mt-2">
          <Badge variant={status.connected ? 'default' : 'destructive'}>
            {status.connected ? (
              <>
                <Check className="h-3 w-3 mr-1" />
                Connected
              </>
            ) : (
              <>
                <X className="h-3 w-3 mr-1" />
                Disconnected
              </>
            )}
          </Badge>
          {status.model && (
            <span className="text-sm text-muted-foreground">
              Model: {status.model}
            </span>
          )}
          {status.error && (
            <span className="text-sm text-destructive">{status.error}</span>
          )}
        </div>
      </div>
    </div>
  )
}
```

### 2. Create ModelSettings Component

Create `frontend/src/components/settings/ModelSettings.tsx`:

```tsx
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useModels, useLLMStatus } from '@/hooks'
import { useChatStore } from '@/stores'
import { RefreshCw, Brain, Check } from 'lucide-react'

export function ModelSettings() {
  const { models, isLoading, refresh } = useModels()
  const { status } = useLLMStatus()
  const { activeModel, setModel } = useChatStore()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Available Models</h3>
          <p className="text-sm text-muted-foreground">
            Models from LM Studio
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : models.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No models available</p>
            <p className="text-sm">Make sure LM Studio is running</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {models.map(model => {
            const isActive = model.id === activeModel
            const displayName = model.id.split('/').pop()?.replace(/-/g, ' ').replace(/\.gguf$/i, '') || model.id

            return (
              <Card
                key={model.id}
                className={`cursor-pointer transition-colors ${isActive ? 'border-primary' : 'hover:bg-muted'}`}
                onClick={() => setModel(model.id)}
              >
                <CardContent className="p-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Brain className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{displayName}</p>
                      <p className="text-xs text-muted-foreground">{model.owned_by}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isActive && (
                      <Badge variant="default">
                        <Check className="h-3 w-3 mr-1" />
                        Active
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Connection Status */}
      {!status.connected && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-sm text-destructive">
            LM Studio is not connected. Start LM Studio and load a model to use chat features.
          </p>
        </div>
      )}
    </div>
  )
}
```

### 3. Create ThemeSettings Component

Create `frontend/src/components/settings/ThemeSettings.tsx`:

```tsx
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { useSettingsStore } from '@/stores'
import { Sun, Moon, Monitor } from 'lucide-react'
import { cn } from '@/lib/utils'

const THEMES = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
] as const

export function ThemeSettings() {
  const { theme, setTheme, fontSize, setFontSize } = useSettingsStore()

  return (
    <div className="space-y-6">
      {/* Theme Selection */}
      <div className="space-y-2">
        <Label>Theme</Label>
        <p className="text-sm text-muted-foreground">
          Choose your preferred color scheme
        </p>
        <div className="grid grid-cols-3 gap-2 mt-2">
          {THEMES.map(t => {
            const Icon = t.icon
            const isActive = theme === t.value

            return (
              <Button
                key={t.value}
                variant={isActive ? 'default' : 'outline'}
                className={cn(
                  'flex flex-col items-center gap-2 h-auto py-4',
                  isActive && 'border-primary'
                )}
                onClick={() => setTheme(t.value)}
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs">{t.label}</span>
              </Button>
            )
          })}
        </div>
      </div>

      {/* Font Size */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Font Size</Label>
          <span className="text-sm text-muted-foreground">{fontSize}px</span>
        </div>
        <p className="text-sm text-muted-foreground">
          Adjust the base font size for the interface
        </p>
        <Slider
          value={[fontSize]}
          onValueChange={([value]) => setFontSize(value)}
          min={12}
          max={20}
          step={1}
          className="mt-4"
        />
        <div className="flex justify-between text-xs text-muted-foreground mt-1">
          <span>Small</span>
          <span>Large</span>
        </div>
      </div>

      {/* Preview */}
      <div className="space-y-2">
        <Label>Preview</Label>
        <div
          className="p-4 border rounded-lg bg-muted"
          style={{ fontSize: `${fontSize}px` }}
        >
          <p>This is how text will appear in the chat.</p>
          <p className="text-muted-foreground text-sm mt-1">
            Secondary text uses a smaller size.
          </p>
        </div>
      </div>
    </div>
  )
}
```

### 4. Create KeyboardSettings Component

Create `frontend/src/components/settings/KeyboardSettings.tsx`:

```tsx
import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useSettingsStore } from '@/stores'
import { Keyboard, RotateCcw } from 'lucide-react'

const DEFAULT_SHORTCUTS: Record<string, string> = {
  newChat: '⌘N',
  commandPalette: '⌘K',
  toggleSidebar: '⌘B',
  toggleSplitView: '⌘\\',
  toggleSettings: '⌘,',
  focusInput: '/',
  sendMessage: 'Enter',
}

const SHORTCUT_LABELS: Record<string, string> = {
  newChat: 'New Chat',
  commandPalette: 'Command Palette',
  toggleSidebar: 'Toggle Sidebar',
  toggleSplitView: 'Toggle Split View',
  toggleSettings: 'Open Settings',
  focusInput: 'Focus Input',
  sendMessage: 'Send Message',
}

export function KeyboardSettings() {
  const { vimMode, toggleVimMode, keyboardShortcuts, updateShortcut, resetToDefaults } = useSettingsStore()
  const [recording, setRecording] = useState<string | null>(null)

  const handleKeyDown = (action: string) => (e: React.KeyboardEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const parts: string[] = []
    if (e.metaKey) parts.push('⌘')
    if (e.ctrlKey) parts.push('Ctrl')
    if (e.altKey) parts.push('Alt')
    if (e.shiftKey) parts.push('Shift')

    // Add the actual key
    if (e.key !== 'Meta' && e.key !== 'Control' && e.key !== 'Alt' && e.key !== 'Shift') {
      const key = e.key.length === 1 ? e.key.toUpperCase() : e.key
      parts.push(key)
    }

    if (parts.length > 0 && parts[parts.length - 1] !== '⌘') {
      updateShortcut(action, parts.join(''))
      setRecording(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Vim Mode */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Label>Vim Mode</Label>
          <p className="text-sm text-muted-foreground">
            Use j/k navigation, i for input mode, etc.
          </p>
        </div>
        <Switch checked={vimMode} onCheckedChange={toggleVimMode} />
      </div>

      <Separator />

      {/* Keyboard Shortcuts */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Label>Keyboard Shortcuts</Label>
            <p className="text-sm text-muted-foreground">
              Click to customize a shortcut
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={resetToDefaults}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
        </div>

        <div className="space-y-2">
          {Object.entries(DEFAULT_SHORTCUTS).map(([action, defaultKey]) => {
            const currentKey = keyboardShortcuts[action] || defaultKey
            const isRecording = recording === action

            return (
              <div
                key={action}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted"
              >
                <span className="text-sm">{SHORTCUT_LABELS[action]}</span>
                <button
                  className={`px-3 py-1.5 rounded border text-sm font-mono min-w-[80px] text-center ${
                    isRecording
                      ? 'border-primary bg-primary/10 animate-pulse'
                      : 'border-border bg-muted hover:bg-background'
                  }`}
                  onClick={() => setRecording(isRecording ? null : action)}
                  onKeyDown={isRecording ? handleKeyDown(action) : undefined}
                  onBlur={() => setRecording(null)}
                >
                  {isRecording ? 'Press keys...' : currentKey}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* Vim Mode Help */}
      {vimMode && (
        <>
          <Separator />
          <div className="space-y-2">
            <Label>Vim Bindings</Label>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Navigate down</span>
                <kbd className="font-mono">j</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Navigate up</span>
                <kbd className="font-mono">k</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Focus input</span>
                <kbd className="font-mono">i</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Search</span>
                <kbd className="font-mono">/</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Exit input</span>
                <kbd className="font-mono">Esc</kbd>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted">
                <span className="text-muted-foreground">Go to top</span>
                <kbd className="font-mono">gg</kbd>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
```

### 5. Create SettingsDialog Component

Create `frontend/src/components/settings/SettingsDialog.tsx`:

```tsx
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { APISettings } from './APISettings'
import { ModelSettings } from './ModelSettings'
import { ThemeSettings } from './ThemeSettings'
import { KeyboardSettings } from './KeyboardSettings'
import { useUIStore } from '@/stores'
import { Settings, Brain, Palette, Keyboard } from 'lucide-react'

export function SettingsDialog() {
  const { settingsOpen, toggleSettings } = useUIStore()

  return (
    <Dialog open={settingsOpen} onOpenChange={toggleSettings}>
      <DialogContent className="max-w-2xl h-[80vh] flex flex-col p-0">
        <DialogHeader className="px-6 py-4 border-b">
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="general" className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid grid-cols-4 mx-6 mt-2">
            <TabsTrigger value="general" className="gap-2">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">General</span>
            </TabsTrigger>
            <TabsTrigger value="models" className="gap-2">
              <Brain className="h-4 w-4" />
              <span className="hidden sm:inline">Models</span>
            </TabsTrigger>
            <TabsTrigger value="theme" className="gap-2">
              <Palette className="h-4 w-4" />
              <span className="hidden sm:inline">Theme</span>
            </TabsTrigger>
            <TabsTrigger value="shortcuts" className="gap-2">
              <Keyboard className="h-4 w-4" />
              <span className="hidden sm:inline">Shortcuts</span>
            </TabsTrigger>
          </TabsList>

          <ScrollArea className="flex-1 px-6 py-4">
            <TabsContent value="general" className="mt-0">
              <APISettings />
            </TabsContent>
            <TabsContent value="models" className="mt-0">
              <ModelSettings />
            </TabsContent>
            <TabsContent value="theme" className="mt-0">
              <ThemeSettings />
            </TabsContent>
            <TabsContent value="shortcuts" className="mt-0">
              <KeyboardSettings />
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
```

### 6. Create Settings Components Index

Create `frontend/src/components/settings/index.ts`:

```tsx
export { SettingsDialog } from './SettingsDialog'
export { APISettings } from './APISettings'
export { ModelSettings } from './ModelSettings'
export { ThemeSettings } from './ThemeSettings'
export { KeyboardSettings } from './KeyboardSettings'
```

### 7. Update MainLayout to Include SettingsDialog

Update `frontend/src/components/layout/MainLayout.tsx`:

```tsx
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from '@/components/sidebar'
import { SettingsDialog } from '@/components/settings'
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

      {/* Settings Dialog */}
      <SettingsDialog />
    </div>
  )
}
```

### 8. Update settingsStore with New Fields

Ensure `frontend/src/stores/settingsStore.ts` has these fields:

```tsx
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SettingsStore {
  theme: 'light' | 'dark' | 'system'
  fontSize: number
  vimMode: boolean
  apiBaseUrl: string
  lmStudioUrl: string
  keyboardShortcuts: Record<string, string>

  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setFontSize: (size: number) => void
  toggleVimMode: () => void
  setApiBaseUrl: (url: string) => void
  setLMStudioUrl: (url: string) => void
  updateShortcut: (action: string, keys: string) => void
  resetToDefaults: () => void
}

const DEFAULT_SHORTCUTS: Record<string, string> = {
  newChat: '⌘N',
  commandPalette: '⌘K',
  toggleSidebar: '⌘B',
  toggleSplitView: '⌘\\',
  toggleSettings: '⌘,',
  focusInput: '/',
  sendMessage: 'Enter',
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      theme: 'dark',
      fontSize: 14,
      vimMode: false,
      apiBaseUrl: 'http://localhost:8000',
      lmStudioUrl: 'http://localhost:1234',
      keyboardShortcuts: { ...DEFAULT_SHORTCUTS },

      setTheme: (theme) => set({ theme }),
      setFontSize: (fontSize) => set({ fontSize }),
      toggleVimMode: () => set((state) => ({ vimMode: !state.vimMode })),
      setApiBaseUrl: (apiBaseUrl) => set({ apiBaseUrl }),
      setLMStudioUrl: (lmStudioUrl) => set({ lmStudioUrl }),
      updateShortcut: (action, keys) =>
        set((state) => ({
          keyboardShortcuts: { ...state.keyboardShortcuts, [action]: keys },
        })),
      resetToDefaults: () =>
        set({
          theme: 'dark',
          fontSize: 14,
          vimMode: false,
          keyboardShortcuts: { ...DEFAULT_SHORTCUTS },
        }),
    }),
    {
      name: 'mai-settings',
    }
  )
)
```

---

## Files to Create

- `frontend/src/components/settings/APISettings.tsx` - API endpoint configuration
- `frontend/src/components/settings/ModelSettings.tsx` - Model management
- `frontend/src/components/settings/ThemeSettings.tsx` - Theme and font settings
- `frontend/src/components/settings/KeyboardSettings.tsx` - Shortcuts and vim mode
- `frontend/src/components/settings/SettingsDialog.tsx` - Main settings dialog
- `frontend/src/components/settings/index.ts` - Exports

## Files to Modify

- `frontend/src/components/layout/MainLayout.tsx` - Add SettingsDialog
- `frontend/src/stores/settingsStore.ts` - Add new fields (if not present)

---

## Success Criteria

```bash
# Verify settings components
ls /Users/maxwell/Projects/MAI/frontend/src/components/settings/
# Expected: APISettings.tsx, ModelSettings.tsx, ThemeSettings.tsx, KeyboardSettings.tsx, SettingsDialog.tsx, index.ts

# Verify TypeScript compiles
cd /Users/maxwell/Projects/MAI/frontend && npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts
```

**Checklist:**
- [ ] Settings dialog opens from header button
- [ ] Four tabs: General, Models, Theme, Shortcuts
- [ ] API Settings shows base URL and LM Studio URL inputs
- [ ] API Settings shows connection status with refresh button
- [ ] Model Settings lists available models from LM Studio
- [ ] Clicking a model sets it as active
- [ ] Theme Settings has light/dark/system buttons
- [ ] Font size slider updates preview text
- [ ] Vim mode toggle works
- [ ] Keyboard shortcuts can be recorded by clicking and pressing keys
- [ ] Reset button restores default shortcuts
- [ ] Settings persist in localStorage

---

## Technical Notes

- **persist middleware**: Zustand persist saves to localStorage
- **Key Recording**: Captures modifier keys + main key on keydown
- **Theme Application**: Theme changes apply via Providers.tsx class toggle
- **Font Size**: Could be applied via CSS variable (--font-size) if desired

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 10-command-palette.md
