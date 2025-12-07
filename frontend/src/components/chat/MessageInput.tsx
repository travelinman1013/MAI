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

    const images = files.filter(f => f.type === 'image').map(f => f.preview!)
    const documents = files.filter(f => f.type === 'document').map(f => f.file.name)

    const userMessage = {
      id: `msg-${Date.now()}`,
      role: 'user' as const,
      content: content.trim(),
      images: images.length > 0 ? images : undefined,
      timestamp: new Date(),
    }

    addMessage(sessionId, userMessage)
    setContent('')
    setFiles([])

    // Simulate response (API integration in later step)
    setStreaming(true)
    setTimeout(() => {
      addMessage(sessionId, {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `I received your message: "${userMessage.content}"${images.length > 0 ? ` with ${images.length} image(s)` : ''}${documents.length > 0 ? ` and ${documents.length} document(s)` : ''}. This is a simulated response - API integration coming soon!`,
        timestamp: new Date(),
      })
      setStreaming(false)
    }, 1500)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border p-4">
      <FileUploadZone onFilesAdded={handleFilesAdded}>
        {files.length > 0 && (
          <div className="flex gap-2 mb-3 flex-wrap">
            {files.map(file => (
              <FilePreview key={file.id} file={file} onRemove={() => removeFile(file.id)} />
            ))}
          </div>
        )}

        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={content}
              onChange={e => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message MAI... (Enter to send, Shift+Enter for new line)"
              className={cn('resize-none min-h-[44px] max-h-[200px] pr-10 pl-10', 'scrollbar-thin scrollbar-thumb-border')}
              rows={1}
              disabled={isStreaming}
            />
          </div>

          <Button type="submit" size="icon" disabled={isStreaming || (!content.trim() && files.length === 0)}>
            {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </FileUploadZone>
    </form>
  )
}
