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
            const displayName = model.name || model.id.split('/').pop()?.replace(/-/g, ' ').replace(/\.gguf$/i, '') || model.id

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
                      <p className="text-xs text-muted-foreground">{model.id}</p>
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
