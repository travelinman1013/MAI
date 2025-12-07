import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useSettingsStore } from '@/stores'
import { useLLMStatus } from '@/hooks'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RefreshCw, Check, X } from 'lucide-react'
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
    apiBaseUrl,
    llmProvider,
    lmStudioUrl,
    ollamaUrl,
    llamacppUrl,
    openaiApiKey,
    setApiBaseUrl,
    setLLMProvider,
    setLMStudioUrl,
    setOllamaUrl,
    setLlamaCppUrl,
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
    </div>
  )
}
