import { useState, useEffect, useCallback, useRef } from 'react'
import {
  getMLXStatus,
  listMLXModels,
  getMLXConfig,
  startMLXServer,
  stopMLXServer,
  restartMLXServer,
  updateMLXConfig,
  type MLXStatus,
  type MLXModel,
  type MLXConfig,
} from '@/services/mlxManager'
import { useSettingsStore } from '@/stores'

interface UseMLXManagerReturn {
  // State
  status: MLXStatus | null
  models: MLXModel[]
  config: MLXConfig | null
  isLoading: boolean
  error: string | null
  managerAvailable: boolean

  // Actions
  start: (model: string) => Promise<boolean>
  stop: () => Promise<boolean>
  restart: (model?: string) => Promise<boolean>
  updateConfig: (config: Partial<Omit<MLXConfig, 'current_model'>>) => Promise<boolean>
  refresh: () => Promise<void>
  refreshModels: () => Promise<void>
}

export function useMLXManager(pollInterval = 5000): UseMLXManagerReturn {
  const mlxManagerUrl = useSettingsStore((state) => state.mlxManagerUrl)
  const setMLXCurrentModel = useSettingsStore((state) => state.setMLXCurrentModel)

  const [status, setStatus] = useState<MLXStatus | null>(null)
  const [models, setModels] = useState<MLXModel[]>([])
  const [config, setConfig] = useState<MLXConfig | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [managerAvailable, setManagerAvailable] = useState(false)

  // Track if we're currently performing an action
  const actionInProgress = useRef(false)

  const fetchStatus = useCallback(async () => {
    if (actionInProgress.current) return

    try {
      const data = await getMLXStatus()
      setStatus(data)
      setManagerAvailable(true)
      setError(null)

      // Update store with current model
      if (data.model) {
        setMLXCurrentModel(data.model)
      }
    } catch (err) {
      setManagerAvailable(false)
      setStatus(null)
      setError(
        err instanceof Error
          ? err.message.includes('Failed to fetch')
            ? 'MLX Manager not running. Start it with: ./scripts/start-mlx-manager.sh'
            : err.message
          : 'Failed to connect to MLX Manager'
      )
    } finally {
      setIsLoading(false)
    }
  }, [setMLXCurrentModel])

  const fetchModels = useCallback(async () => {
    try {
      const data = await listMLXModels()
      setModels(data)
    } catch (err) {
      // Models list might fail if directory doesn't exist, that's okay
      setModels([])
    }
  }, [])

  const fetchConfig = useCallback(async () => {
    try {
      const data = await getMLXConfig()
      setConfig(data)
    } catch {
      // Config fetch might fail if manager not available
    }
  }, [])

  const refresh = useCallback(async () => {
    setIsLoading(true)
    await Promise.all([fetchStatus(), fetchModels(), fetchConfig()])
    setIsLoading(false)
  }, [fetchStatus, fetchModels, fetchConfig])

  const refreshModels = useCallback(async () => {
    await fetchModels()
  }, [fetchModels])

  const start = useCallback(async (model: string): Promise<boolean> => {
    actionInProgress.current = true
    setIsLoading(true)
    setError(null)

    try {
      const result = await startMLXServer(model)
      if (result.success) {
        // Wait a moment for server to start
        await new Promise((resolve) => setTimeout(resolve, 2000))
        await fetchStatus()
        return true
      } else {
        setError(result.message)
        return false
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start server')
      return false
    } finally {
      actionInProgress.current = false
      setIsLoading(false)
    }
  }, [fetchStatus])

  const stop = useCallback(async (): Promise<boolean> => {
    actionInProgress.current = true
    setIsLoading(true)
    setError(null)

    try {
      const result = await stopMLXServer()
      if (result.success) {
        await fetchStatus()
        return true
      } else {
        setError(result.message)
        return false
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop server')
      return false
    } finally {
      actionInProgress.current = false
      setIsLoading(false)
    }
  }, [fetchStatus])

  const restart = useCallback(async (model?: string): Promise<boolean> => {
    actionInProgress.current = true
    setIsLoading(true)
    setError(null)

    try {
      const result = await restartMLXServer(model)
      if (result.success) {
        // Wait a moment for server to restart
        await new Promise((resolve) => setTimeout(resolve, 2000))
        await fetchStatus()
        return true
      } else {
        setError(result.message)
        return false
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart server')
      return false
    } finally {
      actionInProgress.current = false
      setIsLoading(false)
    }
  }, [fetchStatus])

  const updateConfigHandler = useCallback(
    async (configUpdate: Partial<Omit<MLXConfig, 'current_model'>>): Promise<boolean> => {
      setError(null)

      try {
        const updated = await updateMLXConfig(configUpdate)
        setConfig(updated)
        // Refresh models if directory changed
        if (configUpdate.models_directory) {
          await fetchModels()
        }
        return true
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update config')
        return false
      }
    },
    [fetchModels]
  )

  // Initial fetch and polling
  useEffect(() => {
    fetchStatus()
    fetchModels()
    fetchConfig()

    const interval = setInterval(fetchStatus, pollInterval)
    return () => clearInterval(interval)
  }, [fetchStatus, fetchModels, fetchConfig, pollInterval, mlxManagerUrl])

  return {
    status,
    models,
    config,
    isLoading,
    error,
    managerAvailable,
    start,
    stop,
    restart,
    updateConfig: updateConfigHandler,
    refresh,
    refreshModels,
  }
}
