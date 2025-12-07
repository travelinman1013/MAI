# Task: Message Input with File Upload & Streaming Indicator

**Project**: MAI React Frontend (`/Users/maxwell/Projects/MAI`)
**Goal**: Create MessageInput with auto-resize, FileUploadZone with drag-drop, FilePreview, and StreamingIndicator
**Sequence**: 6 of 14
**Depends On**: 05-chat-components.md completed

---

## Archon Task Management (REQUIRED)

### Task Info
- **Task ID**: `2672b645-3c54-412d-bb62-61b1946e44df`
- **Project ID**: `17384994-d1d6-4286-992b-bf82d7485830`

### Update Status
```bash
curl -X PUT "http://localhost:8181/api/tasks/2672b645-3c54-412d-bb62-61b1946e44df" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

curl -X PUT "http://localhost:8181/api/tasks/2672b645-3c54-412d-bb62-61b1946e44df" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the ChatContainer and MessageList in place, we now complete the chat interface with:

- **MessageInput**: Auto-resizing textarea with submit handling
- **FileUploadZone**: Drag-and-drop file upload with visual feedback
- **FilePreview**: Thumbnail preview for images, icons for documents
- **StreamingIndicator**: Animated indicator during AI response streaming

These components enable rich message composition including image and document attachments, which MAI can use for vision models and document analysis.

---

## Requirements

### 1. Create FileUploadZone Component

Create `frontend/src/components/chat/FileUploadZone.tsx`:

```tsx
import { useState, useRef, ReactNode, DragEvent, ChangeEvent } from 'react'
import { cn } from '@/lib/utils'
import { Upload, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface UploadedFile {
  id: string
  file: File
  preview?: string
  type: 'image' | 'document'
}

interface FileUploadZoneProps {
  children: ReactNode
  onFilesAdded: (files: UploadedFile[]) => void
  accept?: string
  maxFiles?: number
}

export function FileUploadZone({
  children,
  onFilesAdded,
  accept = 'image/*,.pdf,.txt,.md,.doc,.docx',
  maxFiles = 10,
}: FileUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const processFiles = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList).slice(0, maxFiles)
    const uploadedFiles: UploadedFile[] = await Promise.all(
      files.map(async (file) => {
        const isImage = file.type.startsWith('image/')
        let preview: string | undefined

        if (isImage) {
          preview = await new Promise((resolve) => {
            const reader = new FileReader()
            reader.onloadend = () => resolve(reader.result as string)
            reader.readAsDataURL(file)
          })
        }

        return {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          file,
          preview,
          type: isImage ? 'image' : 'document',
        }
      })
    )
    onFilesAdded(uploadedFiles)
  }

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer?.files
    if (files && files.length > 0) {
      await processFiles(files)
    }
  }

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      await processFiles(files)
    }
    // Reset input for re-selection of same file
    e.target.value = ''
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        'relative rounded-lg transition-all',
        isDragging && 'ring-2 ring-primary ring-dashed bg-primary/5'
      )}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 bg-primary/10 flex items-center justify-center z-10 rounded-lg">
          <div className="flex flex-col items-center gap-2 text-primary">
            <Upload className="h-8 w-8" />
            <span className="text-sm font-medium">Drop files here</span>
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Children (input area) */}
      {children}

      {/* Attach button */}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute left-2 bottom-2"
        onClick={() => inputRef.current?.click()}
      >
        <Paperclip className="h-4 w-4" />
      </Button>
    </div>
  )
}
```

### 2. Create FilePreview Component

Create `frontend/src/components/chat/FilePreview.tsx`:

```tsx
import { X, FileText, File } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { UploadedFile } from './FileUploadZone'

interface FilePreviewProps {
  file: UploadedFile
  onRemove: () => void
}

export function FilePreview({ file, onRemove }: FilePreviewProps) {
  const getFileIcon = () => {
    const ext = file.file.name.split('.').pop()?.toLowerCase()
    if (['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext || '')) {
      return <FileText className="h-6 w-6" />
    }
    return <File className="h-6 w-6" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="relative group">
      {file.type === 'image' && file.preview ? (
        <div className="relative">
          <img
            src={file.preview}
            alt={file.file.name}
            className="h-16 w-16 object-cover rounded-md border border-border"
          />
          <Button
            type="button"
            variant="destructive"
            size="icon"
            className="absolute -top-2 -right-2 h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={onRemove}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      ) : (
        <div className="relative flex items-center gap-2 p-2 rounded-md border border-border bg-muted">
          <div className="text-muted-foreground">
            {getFileIcon()}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-medium truncate max-w-[100px]">
              {file.file.name}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatFileSize(file.file.size)}
            </span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-5 w-5 ml-auto opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={onRemove}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}
    </div>
  )
}
```

### 3. Create StreamingIndicator Component

Create `frontend/src/components/chat/StreamingIndicator.tsx`:

```tsx
import { cn } from '@/lib/utils'

interface StreamingIndicatorProps {
  className?: string
}

export function StreamingIndicator({ className }: StreamingIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex gap-1">
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce" />
      </div>
      <span className="text-sm text-muted-foreground">MAI is typing...</span>
    </div>
  )
}
```

### 4. Create MessageInput Component

Create `frontend/src/components/chat/MessageInput.tsx`:

```tsx
import { useState, useRef, useEffect, KeyboardEvent, FormEvent } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { FileUploadZone, UploadedFile } from './FileUploadZone'
import { FilePreview } from './FilePreview'
import { useChatStore } from '@/stores'
import { cn } from '@/lib/utils'

interface MessageInputProps {
  sessionId: string
}

export function MessageInput({ sessionId }: MessageInputProps) {
  const [content, setContent] = useState('')
  const [files, setFiles] = useState<UploadedFile[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isStreaming = useChatStore(state => state.isStreaming)
  const addMessage = useChatStore(state => state.addMessage)
  const setStreaming = useChatStore(state => state.setStreaming)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [content])

  const handleFilesAdded = (newFiles: UploadedFile[]) => {
    setFiles(prev => [...prev, ...newFiles].slice(0, 10))
  }

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const handleSubmit = async (e?: FormEvent) => {
    e?.preventDefault()

    if ((!content.trim() && files.length === 0) || isStreaming) return

    // Create user message
    const images = files
      .filter(f => f.type === 'image')
      .map(f => f.preview!)

    const documents = files
      .filter(f => f.type === 'document')
      .map(f => f.file.name)

    const userMessage = {
      id: `msg-${Date.now()}`,
      role: 'user' as const,
      content: content.trim(),
      images: images.length > 0 ? images : undefined,
      documents: documents.length > 0 ? documents : undefined,
      timestamp: Date.now(),
    }

    addMessage(sessionId, userMessage)
    setContent('')
    setFiles([])

    // TODO: Connect to actual API in later step
    // For now, simulate a response
    setStreaming(true)

    setTimeout(() => {
      addMessage(sessionId, {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `I received your message: "${userMessage.content}"${images.length > 0 ? ` with ${images.length} image(s)` : ''}${documents.length > 0 ? ` and ${documents.length} document(s)` : ''}. This is a simulated response - API integration coming soon!`,
        timestamp: Date.now(),
      })
      setStreaming(false)
    }, 1500)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border p-4">
      <FileUploadZone onFilesAdded={handleFilesAdded}>
        {/* File previews */}
        {files.length > 0 && (
          <div className="flex gap-2 mb-3 flex-wrap">
            {files.map(file => (
              <FilePreview
                key={file.id}
                file={file}
                onRemove={() => removeFile(file.id)}
              />
            ))}
          </div>
        )}

        {/* Input area */}
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={content}
              onChange={e => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message MAI... (Enter to send, Shift+Enter for new line)"
              className={cn(
                'resize-none min-h-[44px] max-h-[200px] pr-10 pl-10',
                'scrollbar-thin scrollbar-thumb-border'
              )}
              rows={1}
              disabled={isStreaming}
            />
          </div>

          <Button
            type="submit"
            size="icon"
            disabled={isStreaming || (!content.trim() && files.length === 0)}
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </FileUploadZone>
    </form>
  )
}
```

### 5. Update ChatPanel to Include MessageInput

Update `frontend/src/components/chat/ChatPanel.tsx`:

```tsx
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
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

      {/* Input */}
      <MessageInput sessionId={sessionId} />
    </div>
  )
}
```

### 6. Update Chat Components Index

Update `frontend/src/components/chat/index.ts`:

```tsx
export { ChatContainer } from './ChatContainer'
export { ChatPanel } from './ChatPanel'
export { MessageList } from './MessageList'
export { MessageBubble } from './MessageBubble'
export { MessageInput } from './MessageInput'
export { FileUploadZone } from './FileUploadZone'
export { FilePreview } from './FilePreview'
export { StreamingIndicator } from './StreamingIndicator'
export type { UploadedFile } from './FileUploadZone'
```

### 7. Update MessageList to Use StreamingIndicator

Update `frontend/src/components/chat/MessageList.tsx`:

```tsx
import { useRef, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble } from './MessageBubble'
import { StreamingIndicator } from './StreamingIndicator'
import { useChatStore } from '@/stores'

interface MessageListProps {
  sessionId: string
}

export function MessageList({ sessionId }: MessageListProps) {
  const messages = useChatStore(state => state.messages[sessionId] || [])
  const isStreaming = useChatStore(state => state.isStreaming)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isStreaming])

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

        {isStreaming && <StreamingIndicator className="ml-11" />}

        <div ref={scrollRef} />
      </div>
    </ScrollArea>
  )
}
```

---

## Files to Create

- `frontend/src/components/chat/FileUploadZone.tsx` - Drag-drop upload zone
- `frontend/src/components/chat/FilePreview.tsx` - File thumbnail/icon preview
- `frontend/src/components/chat/StreamingIndicator.tsx` - Typing indicator
- `frontend/src/components/chat/MessageInput.tsx` - Auto-resize input with files

## Files to Modify

- `frontend/src/components/chat/ChatPanel.tsx` - Add MessageInput
- `frontend/src/components/chat/MessageList.tsx` - Use StreamingIndicator
- `frontend/src/components/chat/index.ts` - Export new components

---

## Success Criteria

```bash
# Verify all chat components exist
ls /Users/maxwell/Projects/MAI/frontend/src/components/chat/
# Expected: ChatContainer.tsx, ChatPanel.tsx, MessageList.tsx, MessageBubble.tsx,
#           MessageInput.tsx, FileUploadZone.tsx, FilePreview.tsx, StreamingIndicator.tsx, index.ts

# Verify TypeScript compiles
cd /Users/maxwell/Projects/MAI/frontend && npm run build 2>&1 | grep -i error
# Expected: No errors

# Verify dev server runs
timeout 10 npm run dev 2>&1 || true
# Expected: Vite server starts
```

**Checklist:**
- [ ] MessageInput has auto-resize textarea
- [ ] Textarea submits on Enter, new line on Shift+Enter
- [ ] FileUploadZone shows drag-over visual feedback
- [ ] Files can be dropped or selected via button
- [ ] FilePreview shows image thumbnails
- [ ] FilePreview shows document icons with filename
- [ ] Files can be removed from preview
- [ ] StreamingIndicator shows animated dots
- [ ] Send button is disabled while streaming

---

## Technical Notes

- **Auto-resize**: Textarea height adjusts based on content, max 200px
- **File Previews**: Uses FileReader for image data URLs
- **Simulated Response**: Currently simulates AI response - API integration in later steps
- **Max Files**: Limited to 10 files per message

---

## On Completion

1. Mark Archon task as `done`
2. Verify ALL success criteria pass
3. Next: 07-model-agent-selectors.md
