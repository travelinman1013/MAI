import { Circle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useLLMStatus } from '@/hooks'
import { cn } from '@/lib/utils'

// Map provider IDs to display labels (handles both frontend 'mlx' and backend 'mlxlm')
const providerLabels: Record<string, string> = {
  openai: 'OpenAI',
  lmstudio: 'LM Studio',
  ollama: 'Ollama',
  llamacpp: 'llama.cpp',
  mlx: 'MLX-LM',
  mlxlm: 'MLX-LM',  // Backend returns 'mlxlm'
  auto: 'Auto',
}

const providerColors: Record<string, string> = {
  openai: 'text-green-500',
  lmstudio: 'text-blue-500',
  ollama: 'text-purple-500',
  llamacpp: 'text-orange-500',
  mlx: 'text-cyan-500',
  mlxlm: 'text-cyan-500',  // Backend returns 'mlxlm'
  auto: 'text-gray-500',
}

interface LLMStatusBadgeProps {
  className?: string
}

export function LLMStatusBadge({ className }: LLMStatusBadgeProps) {
  const { status, isLoading, refresh } = useLLMStatus()

  const statusColor = status.connected
    ? 'text-green-500'
    : 'text-red-500'

  const providerLabel = providerLabels[status.provider] || status.provider || 'Unknown'
  const providerColor = providerColors[status.provider] || 'text-gray-500'

  const truncatedModel = status.model
    ? status.model.length > 20
      ? status.model.slice(0, 20) + '...'
      : status.model
    : null

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className={cn('gap-2 px-2', className)}
            onClick={refresh}
            disabled={isLoading}
          >
            {isLoading ? (
              <RefreshCw className="h-3 w-3 animate-spin" />
            ) : (
              <Circle className={cn('h-3 w-3 fill-current', statusColor)} />
            )}
            <span className={cn('text-xs hidden sm:inline', providerColor)}>
              {providerLabel}
            </span>
            {truncatedModel && (
              <span className="text-xs text-muted-foreground hidden md:inline">
                ({truncatedModel})
              </span>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <p><strong>Provider:</strong> {providerLabel}</p>
            <p><strong>Status:</strong> {status.connected ? 'Connected' : 'Disconnected'}</p>
            {status.model && <p><strong>Model:</strong> {status.model}</p>}
            {status.error && <p className="text-red-500"><strong>Error:</strong> {status.error}</p>}
            <p className="text-xs text-muted-foreground mt-2">Click to refresh</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
