import { ChevronDown, Cpu, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useModels } from '@/hooks'
import { useChatStore } from '@/stores'
import { cn } from '@/lib/utils'

interface ModelSelectorProps {
  className?: string
}

export function ModelSelector({ className }: ModelSelectorProps) {
  const { models, isLoading, error, refresh } = useModels()
  const { activeModel, setModel } = useChatStore()

  const selectedModel = models.find(m => m.id === activeModel)
  const displayName = selectedModel?.name || selectedModel?.id || 'Select Model'

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn('gap-2 min-w-[140px] justify-between', className)}
          disabled={isLoading}
        >
          <div className="flex items-center gap-2">
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Cpu className="h-4 w-4" />
            )}
            <span className="truncate max-w-[100px]">{displayName}</span>
          </div>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[200px]">
        <DropdownMenuLabel>Models</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {error ? (
          <DropdownMenuItem onClick={refresh} className="text-destructive">
            Error loading models. Click to retry.
          </DropdownMenuItem>
        ) : models.length === 0 ? (
          <DropdownMenuItem disabled>
            No models available
          </DropdownMenuItem>
        ) : (
          models.map((model) => (
            <DropdownMenuItem
              key={model.id}
              onClick={() => setModel(model.id)}
              className={cn(
                activeModel === model.id && 'bg-accent'
              )}
            >
              <Cpu className="h-4 w-4 mr-2" />
              <span className="truncate">{model.name || model.id}</span>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
