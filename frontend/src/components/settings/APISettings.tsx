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
