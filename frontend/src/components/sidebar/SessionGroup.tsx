import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SessionItem } from './SessionItem'
import { ChatSession } from '@/stores'

interface SessionGroupProps {
  label: string
  sessions: ChatSession[]
  activeSessionId: string | null
  onSelectSession: (id: string) => void
  onRenameSession: (id: string, title: string) => void
  onDeleteSession: (id: string) => void
  defaultExpanded?: boolean
}

export function SessionGroup({
  label,
  sessions,
  activeSessionId,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  defaultExpanded = true,
}: SessionGroupProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <div className="mb-2">
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start px-2 py-1 h-7 text-xs font-medium text-muted-foreground hover:text-foreground"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? (
          <ChevronDown className="h-3.5 w-3.5 mr-1" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 mr-1" />
        )}
        <span className="uppercase tracking-wide">{label}</span>
        <Badge
          variant="secondary"
          className={cn(
            'ml-auto h-5 px-1.5 text-xs font-normal',
            'bg-muted text-muted-foreground'
          )}
        >
          {sessions.length}
        </Badge>
      </Button>

      {isExpanded && (
        <div className="mt-1 space-y-0.5">
          {sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onSelect={onSelectSession}
              onRename={onRenameSession}
              onDelete={onDeleteSession}
            />
          ))}
        </div>
      )}
    </div>
  )
}
