import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { AgentSelector } from './AgentSelector'
import { Button } from '@/components/ui/button'
import { useChatStore, useUIStore } from '@/stores'
import { X, Columns, Maximize2 } from 'lucide-react'

interface ChatPanelProps {
  sessionId: string
  isPrimary: boolean
}

export function ChatPanel({ sessionId, isPrimary }: ChatPanelProps) {
  const session = useChatStore(state =>
    state.sessions.find(s => s.id === sessionId)
  )
  const { splitViewEnabled, toggleSplitView, setSecondarySession } = useUIStore()

  const handleClose = () => {
    if (!isPrimary) {
      setSecondarySession(null)
      if (splitViewEnabled) toggleSplitView()
    }
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Chat Header */}
      <div className="h-12 px-4 flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-3">
          <span className="font-medium truncate max-w-[150px]">
            {session?.title || 'Chat'}
          </span>
          {!isPrimary && (
            <span className="text-xs text-muted-foreground">(Secondary)</span>
          )}
          <AgentSelector compact />
        </div>

        <div className="flex items-center gap-1">
          {isPrimary && !splitViewEnabled && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSplitView}
              title="Split View"
            >
              <Columns className="h-4 w-4" />
            </Button>
          )}
          {!isPrimary && (
            <>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  // Make this the primary session
                  useChatStore.getState().setActiveSession(sessionId)
                }}
                title="Make Primary"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClose}
                title="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList sessionId={sessionId} />
      </div>

      {/* Message Input */}
      <MessageInput sessionId={sessionId} />
    </div>
  )
}
