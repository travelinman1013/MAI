import { SessionGroup } from './SessionGroup'
import { SessionGroup as SessionGroupType } from '@/hooks/useSessions'

interface SessionListProps {
  groups: SessionGroupType[]
  activeSessionId: string | null
  onSelectSession: (id: string) => void
  onRenameSession: (id: string, title: string) => void
  onDeleteSession: (id: string) => void
}

export function SessionList({
  groups,
  activeSessionId,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
}: SessionListProps) {
  if (groups.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <p className="text-sm text-muted-foreground text-center">
          No conversations yet.
          <br />
          Start a new chat to begin.
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-2 py-2">
      {groups.map((group) => (
        <SessionGroup
          key={group.label}
          label={group.label}
          sessions={group.sessions}
          activeSessionId={activeSessionId}
          onSelectSession={onSelectSession}
          onRenameSession={onRenameSession}
          onDeleteSession={onDeleteSession}
        />
      ))}
    </div>
  )
}
