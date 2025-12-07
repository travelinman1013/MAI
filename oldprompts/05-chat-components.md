# Task: Chat Components with Split-View Support

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create ChatContainer with react-resizable-panels split-view, ChatPanel, and refactor MessageList/MessageBubble
**Sequence**: 5 of 14
**Depends On**: 04-layout-routing.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `0464556b-c5a4-4736-8689-7ad451b35dc6`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/0464556b-c5a4-4736-8689-7ad451b35dc6" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/0464556b-c5a4-4736-8689-7ad451b35dc6" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the layout and routing foundation in place, we now build the core chat interface. The existing Chat.tsx and MessageList.tsx components are basic implementations that need enhancement with:

- **Split-view chat**: Side-by-side chat panels using react-resizable-panels
- **ChatContainer**: Orchestrates single or dual chat panels based on uiStore state
- **ChatPanel**: Self-contained chat view with header, messages, and input
- **Enhanced MessageBubble**: Uses shadcn Card and Avatar for polished appearance

The split-view feature allows users to compare conversations or reference one chat while writing in another - a power-user feature common in professional tools.

---

## Requirements

### 1. Install react-resizable-panels

```bash
cd /Users/maxwell/Projects/MAI/frontend
npm install react-resizable-panels
```

### 2. Create ChatContainer Component

Create `frontend/src/components/chat/ChatContainer.tsx`:

```tsx
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { ChatPanel } from './ChatPanel'
import { useUIStore, useChatStore } from '@/stores'

export function ChatContainer() {
  const { splitViewEnabled, secondarySessionId } = useUIStore()
  const { activeSessionId } = useChatStore()

  if (!activeSessionId) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <p>No chat selected. Create a new chat to get started.</p>
      </div>
    )
  }

  return (
    <PanelGroup direction="horizontal" className="h-full">
      <Panel defaultSize={splitViewEnabled ? 50 : 100} minSize={30}>
        <ChatPanel sessionId={activeSessionId} isPrimary />
      </Panel>

      {splitViewEnabled && secondarySessionId && (
        <>
          <PanelResizeHandle className="w-1 bg-border hover:bg-primary/50 transition-colors" />
          <Panel defaultSize={50} minSize={30}>
            <ChatPanel sessionId={secondarySessionId} isPrimary={false} />
          </Panel>
        </>
      )}
    </PanelGroup>
  )
}
```

### 3. Create ChatPanel Component

Create `frontend/src/components/chat/ChatPanel.tsx`:

```tsx
import { MessageList } from './MessageList'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
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
        <div className="flex items-center gap-2">
          <span className="font-medium truncate max-w-[200px]">
            {session?.title || 'Chat'}
          </span>
          {!isPrimary && (
            <span className="text-xs text-muted-foreground">(Secondary)</span>
          )}
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

      {/* Input will be added in 06-message-input-files.md */}
      <div className="p-4 border-t border-border">
        <p className="text-sm text-muted-foreground text-center">
          Message input coming in next step
        </p>
      </div>
    </div>
  )
}
```

### 4. Create Enhanced MessageList

Create `frontend/src/components/chat/MessageList.tsx`:

```tsx
import { useRef, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble } from './MessageBubble'
import { useChatStore } from '@/stores'
import { Loader2 } from 'lucide-react'

interface MessageListProps {
  sessionId: string
}

export function MessageList({ sessionId }: MessageListProps) {
  const messages = useChatStore(state => state.messages[sessionId] || [])
  const isStreaming = useChatStore(state => state.isStreaming)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium">Start a conversation</p>
          <p className="text-sm">Send a message to begin chatting with MAI</p>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isStreaming && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">MAI is thinking...</span>
          </div>
        )}

        <div ref={scrollRef} />
      </div>
    </ScrollArea>
  )
}
```

### 5. Create MessageBubble Component

Create `frontend/src/components/chat/MessageBubble.tsx`:

```tsx
import { Card } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Copy, Check, User, Bot } from 'lucide-react'
import { useState } from 'react'
import type { Message } from '@/types/chat'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className={cn(
          isUser ? 'bg-primary/10' : 'bg-secondary'
        )}>
          {isUser ? (
            <User className="h-4 w-4" />
          ) : (
            <Bot className="h-4 w-4" />
          )}
        </AvatarFallback>
      </Avatar>

      {/* Message Content */}
      <div className={cn('flex flex-col gap-1 max-w-[80%]', isUser && 'items-end')}>
        <Card
          className={cn(
            'p-3 shadow-none',
            isUser ? 'bg-primary/10 border-primary/20' : 'bg-muted'
          )}
        >
          {/* File attachments preview */}
          {message.images && message.images.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {message.images.map((img, idx) => (
                <img
                  key={idx}
                  src={img}
                  alt={`Attachment ${idx + 1}`}
                  className="max-w-[200px] max-h-[150px] rounded-md object-cover"
                />
              ))}
            </div>
          )}

          {/* Message text */}
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
        </Card>

        {/* Actions */}
        <div className={cn(
          'flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity',
          'hover:opacity-100'
        )}>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </Button>
          <span className="text-xs text-muted-foreground">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  )
}
```

### 6. Create Chat Components Index

Create `frontend/src/components/chat/index.ts`:

```tsx
export { ChatContainer } from './ChatContainer'
export { ChatPanel } from './ChatPanel'
export { MessageList } from './MessageList'
export { MessageBubble } from './MessageBubble'
```

### 7. Update ChatPage to Use ChatContainer

Update `frontend/src/pages/ChatPage.tsx`:

```tsx
import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChatContainer } from '@/components/chat'
import { useChatStore } from '@/stores'

export function ChatPage() {
  const { sessionId } = useParams<{ sessionId?: string }>()
  const navigate = useNavigate()
  const {
    sessions,
    activeSessionId,
    setActiveSession,
    createSession
  } = useChatStore()

  useEffect(() => {
    if (sessionId) {
      const exists = sessions.some(s => s.id === sessionId)
      if (exists) {
        setActiveSession(sessionId)
      } else {
        navigate('/', { replace: true })
      }
    } else if (!activeSessionId && sessions.length === 0) {
      const newId = createSession()
      navigate(`/chat/${newId}`, { replace: true })
    } else if (activeSessionId) {
      navigate(`/chat/${activeSessionId}`, { replace: true })
    } else if (sessions.length > 0) {
      setActiveSession(sessions[0].id)
      navigate(`/chat/${sessions[0].id}`, { replace: true })
    }
  }, [sessionId, activeSessionId, sessions, setActiveSession, createSession, navigate])

  return <ChatContainer />
}
```

### 8. Create Directory Structure

```bash
mkdir -p frontend/src/components/chat
```

---

## Files to Create

- `frontend/src/components/chat/ChatContainer.tsx` - Split-view container
- `frontend/src/components/chat/ChatPanel.tsx` - Individual chat panel
- `frontend/src/components/chat/MessageList.tsx` - Enhanced message list
- `frontend/src/components/chat/MessageBubble.tsx` - Styled message bubble
- `frontend/src/components/chat/index.ts` - Exports

## Files to Modify

- `frontend/src/pages/ChatPage.tsx` - Use ChatContainer instead of Chat
- `frontend/package.json` - Add react-resizable-panels (via npm install)

---

## Success Criteria

```bash
# Verify react-resizable-panels installed
cd /Users/maxwell/Projects/MAI/frontend
cat package.json | grep "react-resizable-panels"
# Expected: "react-resizable-panels": "^x.x.x"

# Verify chat components directory
ls /Users/maxwell/Projects/MAI/frontend/src/components/chat/
# Expected: ChatContainer.tsx, ChatPanel.tsx, MessageList.tsx, MessageBubble.tsx, index.ts

# Verify TypeScript compiles
npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts
```

**Checklist:**
- [ ] react-resizable-panels installed
- [ ] ChatContainer renders single panel by default
- [ ] ChatContainer renders split panels when splitViewEnabled=true
- [ ] ChatPanel shows session title in header
- [ ] MessageList renders messages from store
- [ ] MessageBubble shows user messages right-aligned, assistant left-aligned
- [ ] Copy button works on message hover
- [ ] Auto-scroll to latest message works

---

## Technical Notes

- **PanelGroup**: Wraps resizable panels with direction="horizontal"
- **PanelResizeHandle**: Draggable divider between panels
- **ScrollArea**: shadcn wrapper for consistent scrollbar styling
- **Message Type**: Uses existing Message type from `@/types/chat`
- **Store Access**: Uses selective subscriptions for performance

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 06-message-input-files.md
