import { ChevronDown, Bot, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useAgents } from '@/hooks'
import { useChatStore } from '@/stores'
import { cn } from '@/lib/utils'

interface AgentSelectorProps {
  className?: string
  compact?: boolean
}

export function AgentSelector({ className, compact = false }: AgentSelectorProps) {
  const { agents, isLoading, error, refresh } = useAgents()
  const { activeAgent, setAgent } = useChatStore()

  const selectedAgent = agents.find(a => a.name === activeAgent)
  const displayName = selectedAgent?.name || activeAgent || 'Select Agent'

  const triggerButton = (
    <Button
      variant="outline"
      size="sm"
      className={cn(
        'gap-2 justify-between',
        compact ? 'min-w-[100px]' : 'min-w-[140px]',
        className
      )}
      disabled={isLoading}
    >
      <div className="flex items-center gap-2">
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
        <span className="truncate max-w-[80px] capitalize">{displayName}</span>
      </div>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </Button>
  )

  return (
    <DropdownMenu>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              {triggerButton}
            </DropdownMenuTrigger>
          </TooltipTrigger>
          {selectedAgent?.description && (
            <TooltipContent side="bottom">
              <p>{selectedAgent.description}</p>
            </TooltipContent>
          )}
        </Tooltip>
      </TooltipProvider>
      <DropdownMenuContent align="start" className="w-[250px]">
        <DropdownMenuLabel>Agents</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {error ? (
          <DropdownMenuItem onClick={refresh} className="text-destructive">
            Error loading agents. Click to retry.
          </DropdownMenuItem>
        ) : agents.length === 0 ? (
          <DropdownMenuItem disabled>
            No agents available
          </DropdownMenuItem>
        ) : (
          agents.map((agent) => (
            <DropdownMenuItem
              key={agent.name}
              onClick={() => setAgent(agent.name)}
              className={cn(
                'flex flex-col items-start gap-1',
                activeAgent === agent.name && 'bg-accent'
              )}
            >
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4" />
                <span className="capitalize font-medium">{agent.name}</span>
              </div>
              {agent.description && (
                <span className="text-xs text-muted-foreground pl-6 line-clamp-2">
                  {agent.description}
                </span>
              )}
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
