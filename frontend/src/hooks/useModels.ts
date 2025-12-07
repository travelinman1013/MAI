import { useState, useEffect, useCallback } from 'react'
import { getModels } from '@/services/api'

export interface Model {
  id: string
  name: string
}

interface UseModelsReturn {
  models: Model[]
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useModels(): UseModelsReturn {
  const [models, setModels] = useState<Model[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchModels = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await getModels()
      setModels(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch models'))
      setModels([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchModels()
  }, [fetchModels])

  return { models, isLoading, error, refresh: fetchModels }
}
