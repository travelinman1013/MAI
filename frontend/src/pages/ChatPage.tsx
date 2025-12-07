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
