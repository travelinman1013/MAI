import { useState, useEffect, useCallback } from 'react'

export interface UsageDataPoint {
  date: string
  messages: number
  tokens: number
  sessions: number
}

export interface AgentUsageData {
  name: string
  usageCount: number
  avgResponseTime: number
  errorRate: number
}

export interface ModelUsageData {
  name: string
  usageCount: number
  tokens: number
}

export interface AnalyticsData {
  totalMessages: number
  totalSessions: number
  totalTokens: number
  avgResponseTime: number
  usage: UsageDataPoint[]
  agents: AgentUsageData[]
  models: ModelUsageData[]
}

export function useAnalytics(startDate?: Date, endDate?: Date) {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      // Build query params
      const params = new URLSearchParams()
      if (startDate) params.set('start_date', startDate.toISOString())
      if (endDate) params.set('end_date', endDate.toISOString())

      // Fetch all analytics data in parallel
      const [usageRes, agentsRes, modelsRes] = await Promise.all([
        fetch(`/api/v1/analytics/usage?${params}`),
        fetch(`/api/v1/analytics/agents?${params}`),
        fetch(`/api/v1/analytics/models?${params}`),
      ])

      if (!usageRes.ok || !agentsRes.ok || !modelsRes.ok) {
        throw new Error('Failed to fetch analytics')
      }

      const [usage, agents, models] = await Promise.all([
        usageRes.json(),
        agentsRes.json(),
        modelsRes.json(),
      ])

      setData({
        totalMessages: usage.total_messages,
        totalSessions: usage.total_sessions,
        totalTokens: usage.total_tokens,
        avgResponseTime: usage.avg_response_time_ms || 0,
        usage: usage.daily_usage.map((d: { date: string; messages: number; tokens: number; sessions: number }) => ({
          date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          messages: d.messages,
          tokens: d.tokens,
          sessions: d.sessions,
        })),
        agents: agents.agents.map((a: { name: string; usage_count: number; avg_response_time_ms: number | null; error_rate: number }) => ({
          name: a.name,
          usageCount: a.usage_count,
          avgResponseTime: a.avg_response_time_ms || 0,
          errorRate: a.error_rate,
        })),
        models: models.models.map((m: { model_name: string; usage_count: number; total_tokens: number }) => ({
          name: m.model_name,
          usageCount: m.usage_count,
          tokens: m.total_tokens,
        })),
      })
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch analytics'))
    } finally {
      setIsLoading(false)
    }
  }, [startDate, endDate])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, isLoading, error, refresh: fetchData }
}
