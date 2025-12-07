# Task: Model & Agent Selectors with LLM Status

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create ModelSelector with LLM status badge, AgentSelector dropdown, and integrate with stores/API
**Sequence**: 7 of 14
**Depends On**: 06-message-input-files.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `c714ee7b-d514-42a3-b761-11b1cad3db1f`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/c714ee7b-d514-42a3-b761-11b1cad3db1f" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/c714ee7b-d514-42a3-b761-11b1cad3db1f" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the chat interface complete, users need to select which AI model and agent to use. The existing `frontend/src/services/api.ts` already provides:

- `getModels()` - Fetches available LLM models
- `getAgents()` - Fetches available agents
- `getLLMStatus()` - Checks LLM connection status

This task creates the UI components and React hooks to expose these capabilities:

- **ModelSelector**: Dropdown showing available models with connection status badge
- **AgentSelector**: Dropdown for switching between agents (chat, coder, etc.)
- **Custom Hooks**: `useModels()`, `useAgents()`, `useLLMStatus()` with polling

---

## Requirements

### 1. Create useModels Hook

Create `frontend/src/hooks/useModels.ts`:

```tsx
import { useState, useEffect, useCallback } from 'react'
import { getModels } from '@/services/api'

export interface Model {
  id: string
  object: string
  owned_by: string
}

interface UseModelsReturn {
  models: Model[]
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useModels(): UseModelsReturn {
  const [models, setModels] = useState<Model[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchModels = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await getModels()
      setModels(data || [])
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch models'))
      setModels([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchModels()
  }, [fetchModels])

  return { models, isLoading, error, refresh: fetchModels }
}
```

### 2. Create useAgents Hook

Create `frontend/src/hooks/useAgents.ts`:

```tsx
import { useState, useEffect, useCallback } from 'react'
import { getAgents } from '@/services/api'

export interface Agent {
  name: string
  description: string
  system_prompt?: string
}

interface UseAgentsReturn {
  agents: Agent[]
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useAgents(): UseAgentsReturn {
  const [agents, setAgents] = useState<Agent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchAgents = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await getAgents()
      setAgents(data || [])
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch agents'))
      setAgents([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAgents()
  }, [fetchAgents])

  return { agents, isLoading, error, refresh: fetchAgents }
}
```

### 3. Create useLLMStatus Hook with Polling

Create `frontend/src/hooks/useLLMStatus.ts`:

```tsx
import { useState, useEffect, useCallback } from 'react'
import { getLLMStatus } from '@/services/api'

export interface LLMStatus {
  connected: boolean
  model?: string
  error?: string
}

interface UseLLMStatusReturn {
  status: LLMStatus
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useLLMStatus(pollInterval = 30000): UseLLMStatusReturn {
  const [status, setStatus] = useState<LLMStatus>({ connected: false })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setError(null)
      const data = await getLLMStatus()
      setStatus({
        connected: data?.connected ?? false,
        model: data?.model,
        error: data?.error,
      })
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch LLM status'))
      setStatus({ connected: false, error: 'Connection failed' })
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()

    // Poll for status updates
    const interval = setInterval(fetchStatus, pollInterval)
    return () => clearInterval(interval)
  }, [fetchStatus, pollInterval])

  return { status, isLoading, error, refresh: fetchStatus }
}
```

### 4. Create Hooks Index

Create `frontend/src/hooks/index.ts`:

```tsx
export { useModels } from './useModels'
export type { Model } from './useModels'
export { useAgents } from './useAgents'
export type { Agent } from './useAgents'
export { useLLMStatus } from './useLLMStatus'
export type { LLMStatus } from './useLLMStatus'
```

### 5. Create ModelSelector Component

Create `frontend/src/components/chat/ModelSelector.tsx`:

```tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useModels, useLLMStatus } from '@/hooks'
import { useChatStore } from '@/stores'
import { Brain, Loader2, Wifi, WifiOff } from 'lucide-react'

export function ModelSelector() {
  const { models, isLoading: modelsLoading } = useModels()
  const { status, isLoading: statusLoading } = useLLMStatus()
  const { activeModel, setModel } = useChatStore()

  const isLoading = modelsLoading || statusLoading

  if (isLoading) {
    return <Skeleton className="h-9 w-48" />
  }

  return (
    <Select value={activeModel || ''} onValueChange={setModel}>
      <SelectTrigger className="w-48">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 shrink-0" />
          <SelectValue placeholder="Select model">
            {activeModel ? (
              <div className="flex items-center gap-2">
                <Badge
                  variant={status.connected ? 'default' : 'destructive'}
                  className="h-5 px-1.5 text-[10px]"
                >
                  {status.connected ? (
                    <Wifi className="h-3 w-3" />
                  ) : (
                    <WifiOff className="h-3 w-3" />
                  )}
                </Badge>
                <span className="truncate max-w-[100px]">
                  {getModelDisplayName(activeModel)}
                </span>
              </div>
            ) : null}
          </SelectValue>
        </div>
      </SelectTrigger>
      <SelectContent>
        {models.length === 0 ? (
          <div className="px-2 py-4 text-center text-sm text-muted-foreground">
            No models available
          </div>
        ) : (
          models.map(model => (
            <SelectItem key={model.id} value={model.id}>
              <div className="flex flex-col">
                <span>{getModelDisplayName(model.id)}</span>
                <span className="text-xs text-muted-foreground">
                  {model.owned_by}
                </span>
              </div>
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  )
}

function getModelDisplayName(modelId: string): string {
  // Extract human-readable name from model ID
  const name = modelId.split('/').pop() || modelId
  return name.replace(/-/g, ' ').replace(/\.gguf$/i, '')
}
```

### 6. Create AgentSelector Component

Create `frontend/src/components/chat/AgentSelector.tsx`:

```tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useAgents } from '@/hooks'
import { useChatStore } from '@/stores'
import { Bot, Code, MessageSquare, Wrench } from 'lucide-react'

const AGENT_ICONS: Record<string, typeof Bot> = {
  chat: MessageSquare,
  coder: Code,
  tools: Wrench,
  default: Bot,
}

export function AgentSelector() {
  const { agents, isLoading } = useAgents()
  const { activeAgent, setAgent } = useChatStore()

  if (isLoading) {
    return <Skeleton className="h-9 w-40" />
  }

  const getAgentIcon = (agentName: string) => {
    const Icon = AGENT_ICONS[agentName.toLowerCase()] || AGENT_ICONS.default
    return <Icon className="h-4 w-4" />
  }

  return (
    <Select value={activeAgent} onValueChange={setAgent}>
      <SelectTrigger className="w-40">
        <div className="flex items-center gap-2">
          {getAgentIcon(activeAgent)}
          <SelectValue placeholder="Select agent">
            <span className="capitalize">{activeAgent}</span>
          </SelectValue>
        </div>
      </SelectTrigger>
      <SelectContent>
        {agents.length === 0 ? (
          <div className="px-2 py-4 text-center text-sm text-muted-foreground">
            No agents available
          </div>
        ) : (
          agents.map(agent => (
            <SelectItem key={agent.name} value={agent.name}>
              <div className="flex items-center gap-2">
                {getAgentIcon(agent.name)}
                <div className="flex flex-col">
                  <span className="capitalize">{agent.name}</span>
                  {agent.description && (
                    <span className="text-xs text-muted-foreground max-w-[200px] truncate">
                      {agent.description}
                    </span>
                  )}
                </div>
              </div>
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  )
}
```

### 7. Create LLMStatusBadge Component

Create `frontend/src/components/chat/LLMStatusBadge.tsx`:

```tsx
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useLLMStatus } from '@/hooks'
import { Wifi, WifiOff, Loader2 } from 'lucide-react'

export function LLMStatusBadge() {
  const { status, isLoading, refresh } = useLLMStatus()

  if (isLoading) {
    return (
      <Badge variant="secondary">
        <Loader2 className="h-3 w-3 animate-spin mr-1" />
        Checking...
      </Badge>
    )
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant={status.connected ? 'default' : 'destructive'}
            className="cursor-pointer"
            onClick={() => refresh()}
          >
            {status.connected ? (
              <>
                <Wifi className="h-3 w-3 mr-1" />
                Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 mr-1" />
                Offline
              </>
            )}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            {status.connected
              ? `Connected to ${status.model || 'LM Studio'}`
              : status.error || 'LLM not connected'}
          </p>
          <p className="text-xs text-muted-foreground">Click to refresh</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
```

### 8. Update ChatPanel Header with Selectors

Update `frontend/src/components/chat/ChatPanel.tsx`:

```tsx
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { AgentSelector } from './AgentSelector'
import { Button } from '@/components/ui/button'
import { useChatStore, useUIStore } from '@/stores'
import { X, Columns, Maximize2 } from 'lucide-react'

interface ChatPanelProps {
  sessionId: string
  isPrimary: boolean
}

export function ChatPanel({ sessionId, isPrimary }: ChatPanelProps) {
  const session = useChatStore(state =>
    state.sessions.find(s => s.id === sessionId)
  )
  const { splitViewEnabled, toggleSplitView, setSecondarySession } = useUIStore()

  const handleClose = () => {
    if (!isPrimary) {
      setSecondarySession(null)
      if (splitViewEnabled) toggleSplitView()
    }
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Chat Header */}
      <div className="h-12 px-4 flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-3">
          <span className="font-medium truncate max-w-[150px]">
            {session?.title || 'Chat'}
          </span>
          {!isPrimary && (
            <span className="text-xs text-muted-foreground">(Secondary)</span>
          )}
          {isPrimary && <AgentSelector />}
        </div>

        <div className="flex items-center gap-1">
          {isPrimary && !splitViewEnabled && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSplitView}
              title="Split View"
            >
              <Columns className="h-4 w-4" />
            </Button>
          )}
          {!isPrimary && (
            <>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  useChatStore.getState().setActiveSession(sessionId)
                }}
                title="Make Primary"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClose}
                title="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList sessionId={sessionId} />
      </div>

      {/* Input */}
      <MessageInput sessionId={sessionId} />
    </div>
  )
}
```

### 9. Update Header with ModelSelector

Update `frontend/src/components/layout/Header.tsx`:

```tsx
import { PanelLeft, Command, Sun, Moon, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ModelSelector } from '@/components/chat/ModelSelector'
import { LLMStatusBadge } from '@/components/chat/LLMStatusBadge'
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

      {/* Model Selector */}
      <ModelSelector />

      {/* LLM Status */}
      <LLMStatusBadge />

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

### 10. Update Chat Components Index

Update `frontend/src/components/chat/index.ts`:

```tsx
export { ChatContainer } from './ChatContainer'
export { ChatPanel } from './ChatPanel'
export { MessageList } from './MessageList'
export { MessageBubble } from './MessageBubble'
export { MessageInput } from './MessageInput'
export { FileUploadZone } from './FileUploadZone'
export { FilePreview } from './FilePreview'
export { StreamingIndicator } from './StreamingIndicator'
export { ModelSelector } from './ModelSelector'
export { AgentSelector } from './AgentSelector'
export { LLMStatusBadge } from './LLMStatusBadge'
export type { UploadedFile } from './FileUploadZone'
```

---

## Files to Create

- `frontend/src/hooks/useModels.ts` - Models fetching hook
- `frontend/src/hooks/useAgents.ts` - Agents fetching hook
- `frontend/src/hooks/useLLMStatus.ts` - LLM status polling hook
- `frontend/src/hooks/index.ts` - Hooks exports
- `frontend/src/components/chat/ModelSelector.tsx` - Model dropdown
- `frontend/src/components/chat/AgentSelector.tsx` - Agent dropdown
- `frontend/src/components/chat/LLMStatusBadge.tsx` - Status indicator

## Files to Modify

- `frontend/src/components/chat/ChatPanel.tsx` - Add AgentSelector
- `frontend/src/components/layout/Header.tsx` - Add ModelSelector and LLMStatusBadge
- `frontend/src/components/chat/index.ts` - Export new components

---

## Success Criteria

```bash
# Verify hooks directory
ls /Users/maxwell/Projects/MAI/frontend/src/hooks/
# Expected: useModels.ts, useAgents.ts, useLLMStatus.ts, index.ts

# Verify selector components
ls /Users/maxwell/Projects/MAI/frontend/src/components/chat/
# Expected: includes ModelSelector.tsx, AgentSelector.tsx, LLMStatusBadge.tsx

# Verify TypeScript compiles
cd /Users/maxwell/Projects/MAI/frontend && npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts
```

**Checklist:**
- [ ] useModels hook fetches models from API
- [ ] useAgents hook fetches agents from API
- [ ] useLLMStatus polls status every 30 seconds
- [ ] ModelSelector shows available models in dropdown
- [ ] ModelSelector displays connection status badge
- [ ] AgentSelector shows available agents with icons
- [ ] Selecting a model updates chatStore.activeModel
- [ ] Selecting an agent updates chatStore.activeAgent
- [ ] LLMStatusBadge shows connected/offline state
- [ ] Clicking status badge refreshes connection

---

## Technical Notes

- **Existing API**: Uses `frontend/src/services/api.ts` functions
- **Polling**: LLM status polls every 30s to detect connection changes
- **Store Integration**: Selections persist in Zustand chatStore
- **Error Handling**: Gracefully handles API failures with fallback UI
- **Model Names**: Extracts readable names from model IDs

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 08-sidebar-sessions.md
