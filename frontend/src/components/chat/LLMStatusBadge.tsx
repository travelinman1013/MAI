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

interface LLMStatusBadgeProps {
  className?: string
}

export function LLMStatusBadge({ className }: LLMStatusBadgeProps) {
  const { status, isLoading, refresh } = useLLMStatus()

  const statusColor = status.connected
    ? 'text-green-500'
    : 'text-red-500'

  const statusText = status.connected
    ? `Connected${status.model ? ` - ${status.model}` : ''}`
    : status.error || 'Disconnected'

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
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {status.connected ? 'Online' : 'Offline'}
            </span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{statusText}</p>
          <p className="text-xs text-muted-foreground">Click to refresh</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
