import { useState, useEffect, useCallback } from 'react'
import { getAgents } from '@/services/api'

export interface Agent {
  name: string
  description: string
  system_prompt?: string
}

interface UseAgentsReturn {
  agents: Agent[]
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useAgents(): UseAgentsReturn {
  const [agents, setAgents] = useState<Agent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchAgents = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await getAgents()
      setAgents(data || [])
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch agents'))
      setAgents([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAgents()
  }, [fetchAgents])

  return { agents, isLoading, error, refresh: fetchAgents }
}
