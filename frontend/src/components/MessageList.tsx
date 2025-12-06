import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Bot, User } from 'lucide-react'
import { Message } from '@/types/chat'

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <div className="text-center text-gray-400">
          <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <h2 className="text-xl font-medium mb-2">MAI Assistant</h2>
          <p className="text-sm">How can I help you today?</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-4 px-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-4 mb-6 ${
            message.role === 'assistant' ? 'bg-gray-800/50 -mx-4 px-4 py-4 rounded-lg' : ''
          }`}
        >
          <div
            className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              message.role === 'assistant'
                ? 'bg-mai-600 text-white'
                : 'bg-gray-600 text-gray-200'
            }`}
          >
            {message.role === 'assistant' ? (
              <Bot className="h-5 w-5" />
            ) : (
              <User className="h-5 w-5" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{message.content || (isLoading ? '...' : '')}</ReactMarkdown>
            </div>
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
