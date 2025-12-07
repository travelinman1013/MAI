import { useState, useEffect, useCallback } from 'react'

export interface ServiceHealth {
  ok: boolean
  latency_ms?: number
  error?: string
  details?: Record<string, any>
}

export interface DetailedHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  services: {
    redis: ServiceHealth
    postgres: ServiceHealth
    qdrant: ServiceHealth
    llm: ServiceHealth
  }
  total_latency_ms: number
  timestamp: string
  version?: string
}

export function useHealth(pollInterval = 30000) {
  const [health, setHealth] = useState<DetailedHealth | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch('/health/detailed')

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`)
      }

      const data = await response.json()
      setHealth(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch health'))
      // Don't clear existing health data on error - show stale data
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, pollInterval)
    return () => clearInterval(interval)
  }, [fetchHealth, pollInterval])

  return { health, isLoading, error, refresh: fetchHealth }
}
