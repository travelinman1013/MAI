import { useMemo, useState, useCallback } from 'react'
import { isToday, isYesterday, isWithinInterval, subDays, startOfDay } from 'date-fns'
import { useChatStore, ChatSession } from '@/stores'

export interface SessionGroup {
  label: string
  sessions: ChatSession[]
}

export interface UseSessionsReturn {
  sessions: ChatSession[]
  groupedSessions: SessionGroup[]
  searchQuery: string
  setSearchQuery: (query: string) => void
  activeSessionId: string | null
  createSession: () => string
  deleteSession: (id: string) => void
  renameSession: (id: string, title: string) => void
  setActiveSession: (id: string | null) => void
}

function groupSessionsByDate(sessions: ChatSession[]): SessionGroup[] {
  const today: ChatSession[] = []
  const yesterday: ChatSession[] = []
  const lastWeek: ChatSession[] = []
  const older: ChatSession[] = []

  const now = new Date()
  const sevenDaysAgo = startOfDay(subDays(now, 7))
  const twoDaysAgo = startOfDay(subDays(now, 2))

  sessions.forEach(session => {
    const date = new Date(session.updatedAt)

    if (isToday(date)) {
      today.push(session)
    } else if (isYesterday(date)) {
      yesterday.push(session)
    } else if (isWithinInterval(date, { start: sevenDaysAgo, end: twoDaysAgo })) {
      lastWeek.push(session)
    } else {
      older.push(session)
    }
  })

  const groups: SessionGroup[] = []

  if (today.length > 0) {
    groups.push({ label: 'Today', sessions: today })
  }
  if (yesterday.length > 0) {
    groups.push({ label: 'Yesterday', sessions: yesterday })
  }
  if (lastWeek.length > 0) {
    groups.push({ label: 'Last 7 Days', sessions: lastWeek })
  }
  if (older.length > 0) {
    groups.push({ label: 'Older', sessions: older })
  }

  return groups
}

export function useSessions(): UseSessionsReturn {
  const [searchQuery, setSearchQuery] = useState('')

  const {
    sessions,
    activeSessionId,
    createSession,
    deleteSession,
    renameSession,
    setActiveSession,
  } = useChatStore()

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) {
      return sessions
    }

    const query = searchQuery.toLowerCase()
    return sessions.filter(session =>
      session.title.toLowerCase().includes(query)
    )
  }, [sessions, searchQuery])

  const groupedSessions = useMemo(() => {
    // Sort by updatedAt descending before grouping
    const sorted = [...filteredSessions].sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
    return groupSessionsByDate(sorted)
  }, [filteredSessions])

  const handleSetSearchQuery = useCallback((query: string) => {
    setSearchQuery(query)
  }, [])

  return {
    sessions: filteredSessions,
    groupedSessions,
    searchQuery,
    setSearchQuery: handleSetSearchQuery,
    activeSessionId,
    createSession,
    deleteSession,
    renameSession,
    setActiveSession,
  }
}
