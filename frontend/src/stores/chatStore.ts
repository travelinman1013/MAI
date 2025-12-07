import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  images?: string[]
  isStreaming?: boolean
}

export interface ChatSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  agentName: string
  modelId: string | null
}

interface ChatStore {
  // State
  sessions: ChatSession[]
  activeSessionId: string | null
  messages: Record<string, Message[]>
  isStreaming: boolean
  activeAgent: string
  activeModel: string | null

  // Actions
  createSession: () => string
  deleteSession: (id: string) => void
  renameSession: (id: string, title: string) => void
  setActiveSession: (id: string | null) => void
  addMessage: (sessionId: string, message: Message) => void
  updateMessage: (sessionId: string, messageId: string, content: string) => void
  clearMessages: (sessionId: string) => void
  setStreaming: (isStreaming: boolean) => void
  setAgent: (agentName: string) => void
  setModel: (modelId: string | null) => void
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      // Initial state
      sessions: [],
      activeSessionId: null,
      messages: {},
      isStreaming: false,
      activeAgent: 'chat',
      activeModel: null,

      // Actions
      createSession: () => {
        const id = crypto.randomUUID()
        const session: ChatSession = {
          id,
          title: 'New Chat',
          createdAt: new Date(),
          updatedAt: new Date(),
          agentName: get().activeAgent,
          modelId: get().activeModel,
        }
        set(state => ({
          sessions: [session, ...state.sessions],
          activeSessionId: id,
          messages: { ...state.messages, [id]: [] },
        }))
        return id
      },

      deleteSession: (id) => {
        set(state => {
          const { [id]: _, ...remainingMessages } = state.messages
          const sessions = state.sessions.filter(s => s.id !== id)
          return {
            sessions,
            messages: remainingMessages,
            activeSessionId: state.activeSessionId === id
              ? sessions[0]?.id ?? null
              : state.activeSessionId,
          }
        })
      },

      renameSession: (id, title) => {
        set(state => ({
          sessions: state.sessions.map(s =>
            s.id === id ? { ...s, title, updatedAt: new Date() } : s
          ),
        }))
      },

      setActiveSession: (id) => {
        set({ activeSessionId: id })
      },

      addMessage: (sessionId, message) => {
        set(state => ({
          messages: {
            ...state.messages,
            [sessionId]: [...(state.messages[sessionId] || []), message],
          },
          sessions: state.sessions.map(s =>
            s.id === sessionId ? { ...s, updatedAt: new Date() } : s
          ),
        }))
      },

      updateMessage: (sessionId, messageId, content) => {
        set(state => ({
          messages: {
            ...state.messages,
            [sessionId]: (state.messages[sessionId] || []).map(m =>
              m.id === messageId ? { ...m, content } : m
            ),
          },
        }))
      },

      clearMessages: (sessionId) => {
        set(state => ({
          messages: { ...state.messages, [sessionId]: [] },
        }))
      },

      setStreaming: (isStreaming) => set({ isStreaming }),
      setAgent: (agentName) => set({ activeAgent: agentName }),
      setModel: (modelId) => set({ activeModel: modelId }),
    }),
    {
      name: 'mai-chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        messages: state.messages,
        activeSessionId: state.activeSessionId,
        activeAgent: state.activeAgent,
        activeModel: state.activeModel,
      }),
    }
  )
)
