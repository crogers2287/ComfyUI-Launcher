// API client for ComfyUI Launcher backend
import type {
  DownloadInfo,
  DownloadSettings,
  DownloadHistoryItem
} from './types'

// Storage API types
export interface StorageUsage {
  total_size: number // in bytes
  by_type: Record<string, number>
  by_project: Record<string, number>
  models_dir: string
}

// Logs API types
export interface LogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
}

export interface LogsResponse {
  logs: LogEntry[]
  page: number
  per_page: number
  total: number
}

// Model API types
export interface ModelInfo {
  name: string
  path: string
  size: number
  type: string
  hash?: string
  metadata?: Record<string, any>
}

// Workflow API types
export interface WorkflowValidation {
  valid: boolean
  errors?: string[]
  warnings?: string[]
  missing_models?: string[]
  required_nodes?: string[]
}

// API client class
class APIClient {
  private baseURL = '/api'

  private async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Storage APIs
  async getStorageUsage(): Promise<StorageUsage> {
    return this.fetch<StorageUsage>('/storage/usage')
  }

  // Logs APIs
  async getProjectLogs(
    projectId: string,
    options?: {
      page?: number
      per_page?: number
      level?: string
    }
  ): Promise<LogsResponse> {
    const params = new URLSearchParams()
    if (options?.page) params.append('page', options.page.toString())
    if (options?.per_page) params.append('per_page', options.per_page.toString())
    if (options?.level) params.append('level', options.level)

    return this.fetch<LogsResponse>(`/logs/${projectId}?${params}`)
  }

  // Workflow APIs
  async validateWorkflow(workflow: any): Promise<WorkflowValidation> {
    return this.fetch<WorkflowValidation>('/workflow/validate', {
      method: 'POST',
      body: JSON.stringify({ workflow_json: workflow }),
    })
  }

  async importWorkflow(data: {
    url?: string
    file?: File
    project_name: string
    install_missing_models?: boolean
  }): Promise<{ task_id: string; project_id: string }> {
    const formData = new FormData()
    
    if (data.url) {
      formData.append('url', data.url)
    } else if (data.file) {
      formData.append('file', data.file)
    }
    
    formData.append('project_name', data.project_name)
    formData.append('install_missing_models', data.install_missing_models ? 'true' : 'false')

    const response = await fetch(`${this.baseURL}/import_workflow`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Model APIs
  async getModels(type?: string): Promise<ModelInfo[]> {
    const params = type ? `?type=${type}` : ''
    return this.fetch<ModelInfo[]>(`/models${params}`)
  }

  async deleteModel(modelPath: string): Promise<void> {
    await this.fetch(`/models`, {
      method: 'DELETE',
      body: JSON.stringify({ path: modelPath }),
    })
  }

  async downloadModel(data: {
    url: string
    name: string
    type: string
  }): Promise<{ task_id: string }> {
    return this.fetch<{ task_id: string }>('/models/download', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Model Finder APIs
  async findModel(data: {
    filename: string
    model_type?: string
  }): Promise<{
    success: boolean
    query: string
    results: Array<{
      filename: string
      source: 'civitai' | 'huggingface' | 'github' | 'url'
      url: string
      download_url: string
      file_size?: number
      sha256_checksum?: string
      description?: string
      model_type?: string
      relevance_score: number
      metadata?: any
    }>
  }> {
    return this.fetch('/find_model', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async autoResolveModels(workflowJson: any): Promise<{
    success: boolean
    error?: string
    ai_search_enabled?: boolean
    missing_models?: Array<{
      filename: string
      node_type: string
      dest_relative_path: string
      ai_suggestions: Array<{
        filename: string
        source: string
        url: string
        download_url: string
        node_type: string
        sha256_checksum?: string
        relevance_score: number
        hf_file_id?: string
        civitai_file_id?: number
      }>
    }>
  }> {
    return this.fetch('/workflow/auto_resolve_models', {
      method: 'POST',
      body: JSON.stringify({ workflow_json: workflowJson }),
    })
  }

  // Download Management APIs for Issue #12
  async getDownloads(): Promise<{
    success: boolean
    downloads: DownloadInfo[]
    total_count: number
  }> {
    return this.fetch('/downloads')
  }

  async getDownload(downloadId: string): Promise<{
    success: boolean
    download: DownloadInfo
  }> {
    return this.fetch(`/downloads/${downloadId}`)
  }

  async pauseDownload(downloadId: string): Promise<{
    success: boolean
    message: string
  }> {
    return this.fetch(`/downloads/${downloadId}/pause`, {
      method: 'POST',
    })
  }

  async resumeDownload(downloadId: string): Promise<{
    success: boolean
    message: string
  }> {
    return this.fetch(`/downloads/${downloadId}/resume`, {
      method: 'POST',
    })
  }

  async cancelDownload(downloadId: string): Promise<{
    success: boolean
    message: string
  }> {
    return this.fetch(`/downloads/${downloadId}/cancel`, {
      method: 'POST',
    })
  }

  async getDownloadSettings(): Promise<{
    success: boolean
    settings: DownloadSettings
  }> {
    return this.fetch('/downloads/settings')
  }

  async updateDownloadSettings(settings: Partial<DownloadSettings>): Promise<{
    success: boolean
    message: string
  }> {
    return this.fetch('/downloads/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    })
  }

  async getDownloadHistory(): Promise<{
    success: boolean
    history: DownloadHistoryItem[]
    total_count: number
  }> {
    return this.fetch('/downloads/history')
  }
}

// Export singleton instance
export const apiClient = new APIClient()