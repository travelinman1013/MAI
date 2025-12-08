/**
 * MLX-LM Manager API Client
 *
 * Client for the host-side MLX Manager service (port 8082).
 * Provides process management for the MLX-LM server.
 */

import { useSettingsStore } from '@/stores'

// ============================================================================
// Types
// ============================================================================

export interface MLXStatus {
  running: boolean
  pid: number | null
  model: string | null
  port: number
  uptime_seconds: number | null
  health_ok: boolean
}

export interface MLXModel {
  name: string
  path: string
  size: string
}

export interface MLXConfig {
  models_directory: string
  port: number
  host: string
  current_model: string | null
}

export interface MLXActionResponse {
  success: boolean
  message: string
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the MLX Manager URL from settings store
 */
function getManagerUrl(): string {
  const { mlxManagerUrl } = useSettingsStore.getState()
  return mlxManagerUrl
}

/**
 * Make a fetch request to the MLX Manager with error handling
 */
async function managerFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const baseUrl = getManagerUrl()
  const url = `${baseUrl}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // Ignore JSON parse errors
    }
    throw new Error(errorMessage)
  }

  return response.json()
}

// ============================================================================
// Status API
// ============================================================================

/**
 * Get MLX-LM server status
 * @returns Server status including running state, PID, model, and uptime
 */
export async function getMLXStatus(): Promise<MLXStatus> {
  return managerFetch<MLXStatus>('/status')
}

// ============================================================================
// Server Control API
// ============================================================================

/**
 * Start MLX-LM server with specified model
 * @param model - Model name to load
 * @returns Action response with success/failure status
 */
export async function startMLXServer(model: string): Promise<MLXActionResponse> {
  return managerFetch<MLXActionResponse>('/start', {
    method: 'POST',
    body: JSON.stringify({ model }),
  })
}

/**
 * Stop MLX-LM server gracefully
 * @returns Action response with success/failure status
 */
export async function stopMLXServer(): Promise<MLXActionResponse> {
  return managerFetch<MLXActionResponse>('/stop', {
    method: 'POST',
  })
}

/**
 * Restart MLX-LM server, optionally with a new model
 * @param model - Optional new model to load on restart
 * @returns Action response with success/failure status
 */
export async function restartMLXServer(model?: string): Promise<MLXActionResponse> {
  return managerFetch<MLXActionResponse>('/restart', {
    method: 'POST',
    body: model ? JSON.stringify({ model }) : JSON.stringify({}),
  })
}

// ============================================================================
// Models API
// ============================================================================

/**
 * List available MLX models in the configured directory
 * @returns Array of available models with name, path, and size
 */
export async function listMLXModels(): Promise<MLXModel[]> {
  return managerFetch<MLXModel[]>('/models')
}

// ============================================================================
// Configuration API
// ============================================================================

/**
 * Get current MLX Manager configuration
 * @returns Current configuration
 */
export async function getMLXConfig(): Promise<MLXConfig> {
  return managerFetch<MLXConfig>('/config')
}

/**
 * Update MLX Manager configuration
 * @param config - Partial configuration to update
 * @returns Updated configuration
 */
export async function updateMLXConfig(
  config: Partial<Omit<MLXConfig, 'current_model'>>
): Promise<MLXConfig> {
  return managerFetch<MLXConfig>('/config', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

// ============================================================================
// Health Check
// ============================================================================

/**
 * Check if the MLX Manager service is reachable
 * @returns True if manager is responding, false otherwise
 */
export async function isMLXManagerAvailable(): Promise<boolean> {
  try {
    await getMLXStatus()
    return true
  } catch {
    return false
  }
}
