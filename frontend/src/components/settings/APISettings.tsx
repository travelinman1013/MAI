import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useSettingsStore } from '@/stores'
import { useLLMStatus, useMLXManager } from '@/hooks'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RefreshCw, Check, X, Play, Square, RotateCcw, FolderOpen, Loader2 } from 'lucide-react'
import type { LLMProvider } from '@/types/chat'

const providers: { value: LLMProvider; label: string; description: string }[] = [
  { value: 'auto', label: 'Auto-detect', description: 'Automatically detect available provider' },
  { value: 'openai', label: 'OpenAI', description: 'OpenAI API (requires API key)' },
  { value: 'lmstudio', label: 'LM Studio', description: 'Local LM Studio server' },
  { value: 'ollama', label: 'Ollama', description: 'Local Ollama server' },
  { value: 'llamacpp', label: 'llama.cpp', description: 'Local llama.cpp server' },
  { value: 'mlx', label: 'MLX-LM', description: 'Apple Silicon local inference via MLX' },
]

export function APISettings() {
  const {
    apiBaseUrl,
    llmProvider,
    lmStudioUrl,
    ollamaUrl,
    llamacppUrl,
    mlxUrl,
    openaiApiKey,
    setApiBaseUrl,
    setLLMProvider,
    setLMStudioUrl,
    setOllamaUrl,
    setLlamaCppUrl,
    setMLXUrl,
    setOpenAIApiKey,
  } = useSettingsStore()
  const { status, refresh, isLoading } = useLLMStatus()

  return (
    <div className="space-y-6">
      {/* API Base URL */}
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

          {/* Connection Status */}
          <div className="flex items-center gap-2">
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
            <Button variant="ghost" size="icon" onClick={refresh} disabled={isLoading} className="ml-auto">
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
          {status.error && (
            <p className="text-sm text-destructive">{status.error}</p>
          )}
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
              <p className="text-xs text-muted-foreground">
                Note: API key is stored locally for reference. Backend uses environment variables.
              </p>
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

      {/* MLX-LM Settings */}
      {(llmProvider === 'mlx' || llmProvider === 'auto') && (
        <MLXLMSettings mlxUrl={mlxUrl} setMLXUrl={setMLXUrl} />
      )}
    </div>
  )
}

// ============================================================================
// MLX-LM Settings Component
// ============================================================================

interface MLXLMSettingsProps {
  mlxUrl: string
  setMLXUrl: (url: string) => void
}

function MLXLMSettings({ mlxUrl, setMLXUrl }: MLXLMSettingsProps) {
  const {
    mlxModelsDirectory,
    mlxManagerUrl,
    setMLXModelsDirectory,
    setMLXManagerUrl,
  } = useSettingsStore()

  const {
    status,
    models,
    isLoading,
    error,
    managerAvailable,
    start,
    stop,
    restart,
    updateConfig,
    refresh,
    refreshModels,
  } = useMLXManager()

  const [selectedModel, setSelectedModel] = useState<string>('')
  const [localModelsDir, setLocalModelsDir] = useState(mlxModelsDirectory)

  // Helper to format uptime
  const formatUptime = (seconds: number | null) => {
    if (!seconds) return ''
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    if (mins > 60) {
      const hours = Math.floor(mins / 60)
      return `${hours}h ${mins % 60}m`
    }
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  const handleStartServer = async () => {
    const modelToStart = selectedModel || (models.length > 0 ? models[0].name : '')
    if (modelToStart) {
      await start(modelToStart)
    }
  }

  const handleModelChange = async (model: string) => {
    setSelectedModel(model)
    // If server is running, restart with new model
    if (status?.running && model !== status.model) {
      await restart(model)
    }
  }

  const handleUpdateModelsDirectory = async () => {
    if (localModelsDir !== mlxModelsDirectory) {
      setMLXModelsDirectory(localModelsDir)
      await updateConfig({ models_directory: localModelsDir })
      await refreshModels()
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>MLX-LM</CardTitle>
            <CardDescription>Configure MLX-LM server (Apple Silicon)</CardDescription>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={refresh}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Manager Status */}
        <div className="flex items-center gap-2 flex-wrap">
          {managerAvailable ? (
            <>
              <Badge variant={status?.running ? 'default' : 'secondary'}>
                {status?.running ? (
                  <>
                    <Check className="h-3 w-3 mr-1" />
                    Running
                  </>
                ) : (
                  <>
                    <X className="h-3 w-3 mr-1" />
                    Stopped
                  </>
                )}
              </Badge>
              {status?.pid && (
                <span className="text-xs text-muted-foreground">PID: {status.pid}</span>
              )}
              {status?.uptime_seconds && (
                <span className="text-xs text-muted-foreground">
                  Uptime: {formatUptime(status.uptime_seconds)}
                </span>
              )}
              {status?.model && (
                <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                  Model: {status.model}
                </span>
              )}
            </>
          ) : (
            <Badge variant="outline">
              Manager Offline
            </Badge>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {/* Server Controls */}
        {managerAvailable && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartServer}
              disabled={isLoading || status?.running || models.length === 0}
            >
              <Play className="h-4 w-4 mr-1" />
              Start
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={stop}
              disabled={isLoading || !status?.running}
            >
              <Square className="h-4 w-4 mr-1" />
              Stop
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => restart()}
              disabled={isLoading || !status?.running}
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              Restart
            </Button>
          </div>
        )}

        {/* Model Selection */}
        {managerAvailable && (
          <div className="space-y-2">
            <Label htmlFor="mlx-model">Model</Label>
            <div className="flex gap-2">
              <Select
                value={selectedModel || status?.model || ''}
                onValueChange={handleModelChange}
                disabled={models.length === 0}
              >
                <SelectTrigger id="mlx-model" className="flex-1">
                  <SelectValue placeholder={models.length === 0 ? 'No models found' : 'Select model'} />
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => (
                    <SelectItem key={model.name} value={model.name}>
                      <div className="flex justify-between items-center gap-4 w-full">
                        <span className="truncate">{model.name}</span>
                        <span className="text-xs text-muted-foreground">{model.size}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="ghost"
                size="icon"
                onClick={refreshModels}
                title="Refresh models list"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            {models.length === 0 && managerAvailable && (
              <p className="text-xs text-muted-foreground">
                No models found. Check the models directory path below.
              </p>
            )}
          </div>
        )}

        {/* Server URL */}
        <div className="space-y-2">
          <Label htmlFor="mlx-url">Server URL</Label>
          <Input
            id="mlx-url"
            type="url"
            placeholder="http://localhost:8081"
            value={mlxUrl}
            onChange={(e) => setMLXUrl(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            MLX-LM server endpoint (default port: 8081)
          </p>
        </div>

        {/* Manager URL */}
        <div className="space-y-2">
          <Label htmlFor="mlx-manager-url">Manager URL</Label>
          <Input
            id="mlx-manager-url"
            type="url"
            placeholder="http://localhost:8082"
            value={mlxManagerUrl}
            onChange={(e) => setMLXManagerUrl(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            MLX Manager service (start with: ./scripts/start-mlx-manager.sh)
          </p>
        </div>

        {/* Models Directory */}
        <div className="space-y-2">
          <Label htmlFor="mlx-models-dir">Models Directory</Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="mlx-models-dir"
                className="pl-9"
                placeholder="/path/to/models"
                value={localModelsDir}
                onChange={(e) => setLocalModelsDir(e.target.value)}
                onBlur={handleUpdateModelsDirectory}
                onKeyDown={(e) => e.key === 'Enter' && handleUpdateModelsDirectory()}
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Directory containing MLX model folders (press Enter to apply)
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
