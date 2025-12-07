# Task: Update Frontend for Multi-Provider Support

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Update React frontend to support provider selection and display
**Sequence**: 8 of 10
**Depends On**: 07-docker-integration.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `[TO_BE_ASSIGNED]`
- **Project ID**: `[TO_BE_ASSIGNED]`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The backend now supports multiple LLM providers. The frontend needs to be updated to:
1. Display the current provider in the status badge
2. Allow provider selection in settings
3. Show available providers
4. Configure provider-specific URLs

The frontend is a React app with TypeScript, using Zustand for state management and shadcn/ui components.

---

## Requirements

### 1. Update Type Definitions

Update `frontend/src/types/chat.ts`:

```typescript
// Add LLM provider type
export type LLMProvider = 'openai' | 'lmstudio' | 'ollama' | 'llamacpp' | 'auto'

// Update LLMStatus interface
export interface LLMStatus {
  connected: boolean
  model: string | null
  provider: LLMProvider
  availableProviders?: LLMProvider[]
  error?: string | null
  metadata?: Record<string, unknown>
}

// Add provider config interface
export interface ProviderConfig {
  type: LLMProvider
  baseUrl: string
  modelName?: string
}

// Add provider status interface
export interface ProviderStatus {
  name: LLMProvider
  connected: boolean
  model: string | null
  error: string | null
  baseUrl: string | null
}
```

### 2. Update Settings Store

Update `frontend/src/stores/settingsStore.ts`:

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LLMProvider } from '@/types/chat'

interface SettingsStore {
  // Existing settings...
  theme: 'light' | 'dark' | 'system'
  lmStudioUrl: string

  // New provider settings
  llmProvider: LLMProvider
  ollamaUrl: string
  llamacppUrl: string
  openaiApiKey: string

  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setLMStudioUrl: (url: string) => void
  setLLMProvider: (provider: LLMProvider) => void
  setOllamaUrl: (url: string) => void
  setLlamaCppUrl: (url: string) => void
  setOpenAIApiKey: (key: string) => void
  resetSettings: () => void
}

const DEFAULT_SETTINGS = {
  theme: 'system' as const,
  lmStudioUrl: 'http://localhost:1234',
  llmProvider: 'auto' as LLMProvider,
  ollamaUrl: 'http://localhost:11434',
  llamacppUrl: 'http://localhost:8080',
  openaiApiKey: '',
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,

      setTheme: (theme) => set({ theme }),
      setLMStudioUrl: (url) => set({ lmStudioUrl: url }),
      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setOllamaUrl: (url) => set({ ollamaUrl: url }),
      setLlamaCppUrl: (url) => set({ llamacppUrl: url }),
      setOpenAIApiKey: (key) => set({ openaiApiKey: key }),
      resetSettings: () => set(DEFAULT_SETTINGS),
    }),
    {
      name: 'mai-settings',
    }
  )
)
```

### 3. Update LLM Status Hook

Update `frontend/src/hooks/useLLMStatus.ts`:

```typescript
import { useState, useEffect, useCallback } from 'react'
import type { LLMStatus, LLMProvider } from '@/types/chat'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useLLMStatus(pollInterval = 30000) {
  const [status, setStatus] = useState<LLMStatus>({
    connected: false,
    model: null,
    provider: 'auto',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/llm-status`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      setStatus({
        connected: data.connected,
        model: data.model_name || null,
        provider: data.provider as LLMProvider,
        availableProviders: data.available_providers as LLMProvider[],
        error: data.error,
        metadata: data.metadata,
      })
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status')
      setStatus((prev) => ({ ...prev, connected: false }))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, pollInterval)
    return () => clearInterval(interval)
  }, [fetchStatus, pollInterval])

  return { status, loading, error, refresh: fetchStatus }
}
```

### 4. Update LLM Status Badge

Update `frontend/src/components/chat/LLMStatusBadge.tsx`:

```typescript
import { cn } from '@/lib/utils'
import { useLLMStatus } from '@/hooks/useLLMStatus'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Circle, Loader2 } from 'lucide-react'
import type { LLMProvider } from '@/types/chat'

const providerLabels: Record<LLMProvider, string> = {
  openai: 'OpenAI',
  lmstudio: 'LM Studio',
  ollama: 'Ollama',
  llamacpp: 'llama.cpp',
  auto: 'Auto',
}

const providerColors: Record<LLMProvider, string> = {
  openai: 'text-green-500',
  lmstudio: 'text-blue-500',
  ollama: 'text-purple-500',
  llamacpp: 'text-orange-500',
  auto: 'text-gray-500',
}

export function LLMStatusBadge() {
  const { status, loading } = useLLMStatus()

  if (loading) {
    return (
      <Badge variant="outline" className="gap-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Checking...</span>
      </Badge>
    )
  }

  const providerLabel = providerLabels[status.provider] || status.provider
  const providerColor = providerColors[status.provider] || 'text-gray-500'

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant={status.connected ? 'default' : 'destructive'}
            className="gap-1 cursor-help"
          >
            <Circle
              className={cn(
                'h-2 w-2 fill-current',
                status.connected ? 'text-green-500' : 'text-red-500'
              )}
            />
            <span className={providerColor}>{providerLabel}</span>
            {status.model && (
              <span className="text-muted-foreground text-xs ml-1">
                ({status.model.length > 20
                  ? status.model.slice(0, 20) + '...'
                  : status.model})
              </span>
            )}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <p><strong>Provider:</strong> {providerLabel}</p>
            <p><strong>Status:</strong> {status.connected ? 'Connected' : 'Disconnected'}</p>
            {status.model && <p><strong>Model:</strong> {status.model}</p>}
            {status.error && <p className="text-red-500"><strong>Error:</strong> {status.error}</p>}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
```

### 5. Update API Settings Component

Update `frontend/src/components/settings/APISettings.tsx`:

```typescript
import { useSettingsStore } from '@/stores/settingsStore'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { LLMProvider } from '@/types/chat'

const providers: { value: LLMProvider; label: string; description: string }[] = [
  { value: 'auto', label: 'Auto-detect', description: 'Automatically detect available provider' },
  { value: 'openai', label: 'OpenAI', description: 'OpenAI API (requires API key)' },
  { value: 'lmstudio', label: 'LM Studio', description: 'Local LM Studio server' },
  { value: 'ollama', label: 'Ollama', description: 'Local Ollama server' },
  { value: 'llamacpp', label: 'llama.cpp', description: 'Local llama.cpp server' },
]

export function APISettings() {
  const {
    llmProvider,
    lmStudioUrl,
    ollamaUrl,
    llamacppUrl,
    openaiApiKey,
    setLLMProvider,
    setLMStudioUrl,
    setOllamaUrl,
    setLlamaCppUrl,
    setOpenAIApiKey,
  } = useSettingsStore()

  return (
    <div className="space-y-6">
      {/* Provider Selection */}
      <Card>
        <CardHeader>
          <CardTitle>LLM Provider</CardTitle>
          <CardDescription>
            Select which LLM provider to use for chat completions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="provider">Provider</Label>
            <Select
              value={llmProvider}
              onValueChange={(value) => setLLMProvider(value as LLMProvider)}
            >
              <SelectTrigger id="provider">
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    <div className="flex flex-col">
                      <span>{p.label}</span>
                      <span className="text-xs text-muted-foreground">{p.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* OpenAI Settings */}
      {(llmProvider === 'openai' || llmProvider === 'auto') && (
        <Card>
          <CardHeader>
            <CardTitle>OpenAI</CardTitle>
            <CardDescription>Configure OpenAI API access</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="openai-key">API Key</Label>
              <Input
                id="openai-key"
                type="password"
                placeholder="sk-..."
                value={openaiApiKey}
                onChange={(e) => setOpenAIApiKey(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* LM Studio Settings */}
      {(llmProvider === 'lmstudio' || llmProvider === 'auto') && (
        <Card>
          <CardHeader>
            <CardTitle>LM Studio</CardTitle>
            <CardDescription>Configure LM Studio server connection</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="lmstudio-url">Server URL</Label>
              <Input
                id="lmstudio-url"
                type="url"
                placeholder="http://localhost:1234"
                value={lmStudioUrl}
                onChange={(e) => setLMStudioUrl(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ollama Settings */}
      {(llmProvider === 'ollama' || llmProvider === 'auto') && (
        <Card>
          <CardHeader>
            <CardTitle>Ollama</CardTitle>
            <CardDescription>Configure Ollama server connection</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="ollama-url">Server URL</Label>
              <Input
                id="ollama-url"
                type="url"
                placeholder="http://localhost:11434"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* llama.cpp Settings */}
      {(llmProvider === 'llamacpp' || llmProvider === 'auto') && (
        <Card>
          <CardHeader>
            <CardTitle>llama.cpp</CardTitle>
            <CardDescription>Configure llama.cpp server connection</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="llamacpp-url">Server URL</Label>
              <Input
                id="llamacpp-url"
                type="url"
                placeholder="http://localhost:8080"
                value={llamacppUrl}
                onChange={(e) => setLlamaCppUrl(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
```

---

## Files to Modify

- `frontend/src/types/chat.ts` - Add provider types
- `frontend/src/stores/settingsStore.ts` - Add provider settings
- `frontend/src/hooks/useLLMStatus.ts` - Update to handle new fields
- `frontend/src/components/chat/LLMStatusBadge.tsx` - Show provider info
- `frontend/src/components/settings/APISettings.tsx` - Add provider selection

---

## Success Criteria

```bash
# Verify TypeScript compiles without errors
cd frontend && npm run build 2>&1 | tail -5
# Expected: Build successful (no type errors)

# Verify types are correct
cd frontend && npx tsc --noEmit
# Expected: No errors

# Check that components exist
test -f frontend/src/components/settings/APISettings.tsx && echo "APISettings OK"
# Expected: APISettings OK
```

**Checklist:**
- [ ] LLMProvider type added to chat.ts
- [ ] LLMStatus interface updated with provider field
- [ ] SettingsStore has llmProvider, ollamaUrl, llamacppUrl
- [ ] useLLMStatus returns provider information
- [ ] LLMStatusBadge displays provider name and color
- [ ] APISettings has provider selector
- [ ] Provider-specific URL inputs shown conditionally
- [ ] TypeScript compiles without errors

---

## Technical Notes

- **Provider Colors**: Each provider has a distinct color for visual identification
- **Conditional Rendering**: Show provider settings only when relevant
- **Persistence**: Settings are persisted to localStorage via Zustand persist
- **Truncation**: Long model names are truncated in the badge

---

## Important

- Do NOT break existing functionality
- Settings changes are local only - backend configuration comes from environment
- The frontend settings are for display/reference, not for changing backend config
- Handle cases where provider info is missing from API response

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (09-unit-tests.md) depends on this completing successfully
