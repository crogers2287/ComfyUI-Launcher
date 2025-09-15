/**
 * Comprehensive frontend recovery tests for ComfyUI Launcher Issue #8.
 * 
 * These tests cover all frontend recovery scenarios including:
 * 1. Network interruption during download
 * 2. Browser refresh during operation  
 * 3. State persistence and restoration
 * 4. WebSocket reconnection recovery
 * 5. UI state recovery after errors
 * 6. Concurrent operation handling
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { toast } from 'sonner'
import userEvent from '@testing-library/user-event'
import { vi, beforeEach, describe, test, expect } from 'vitest'

// Import components to test
import { DownloadDashboard } from '@/components/DownloadDashboard'
import { ModelManager } from '@/components/ModelManager'
import { ImportWorkflowUI } from '@/components/ImportWorkflowUI'
import { NewWorkflowUI } from '@/components/NewWorkflowUI'
import { LiveLogViewer } from '@/components/LiveLogViewer'

// Mock API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    getDownloads: vi.fn(),
    getDownloadSettings: vi.fn(),
    pauseDownload: vi.fn(),
    resumeDownload: vi.fn(),
    cancelDownload: vi.fn(),
    startDownload: vi.fn(),
    getModels: vi.fn(),
    downloadModel: vi.fn(),
    importWorkflow: vi.fn(),
    createProject: vi.fn(),
    getProjects: vi.fn(),
    getLogs: vi.fn(),
  }
}))

// Mock masonic library
vi.mock('masonic', () => ({
  Masonry: vi.fn(({ children }) => <div>{children}</div>)
}))

// Mock socket client
vi.mock('@/lib/socket', () => ({
  socket: {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
  }
}))

// Import mocked instances
import { apiClient } from '@/lib/api'
import { socket } from '@/lib/socket'

// Mock local storage
const mockLocalStorage = {
  store: {},
  getItem: vi.fn((key) => mockLocalStorage.store[key]),
  setItem: vi.fn((key, value) => {
    mockLocalStorage.store[key] = value
  }),
  removeItem: vi.fn((key) => {
    delete mockLocalStorage.store[key]
  }),
  clear: vi.fn(() => {
    mockLocalStorage.store = {}
  })
}

// Mock IndexedDB for larger state persistence
const mockIndexedDB = {
  databases: {},
  open: vi.fn((name, version) => {
    return {
      onsuccess: null,
      onerror: null,
      onupgradeneeded: null,
    }
  })
}

// Set up global mocks
Object.defineProperty(global, 'localStorage', {
  value: mockLocalStorage,
  configurable: true,
})

Object.defineProperty(global, 'indexedDB', {
  value: mockIndexedDB,
  configurable: true,
})

const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        retryDelay: 100,
      },
      mutations: {
        retry: 1,
        retryDelay: 100,
      }
    }
  })
}

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient()
  
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('Download Recovery Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocalStorage.clear()
    toast.success = vi.fn()
    toast.error = vi.fn()
  })

  describe('Network Interruption Recovery', () => {
    test('should recover from network interruption during download', async () => {
      const mockApi = apiClient
      
      // Simulate network interruption then recovery
      let callCount = 0
      mockApi.getDownloads.mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          // First call - network error
          return Promise.reject(new Error('Network error'))
        } else {
          // Subsequent calls - success
          return Promise.resolve({
            downloads: [
              {
                id: 'download_1',
                status: 'downloading',
                progress: 45,
                speed: 2.5,
                eta: 120,
                url: 'https://example.com/model.bin',
                filename: 'model.bin',
                size: 1000000000,
                downloaded: 450000000,
                error: null,
                retries: 1
              }
            ]
          })
        }
      })

      renderWithProviders(<DownloadDashboard />)
      
      // Should show error initially
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringContaining('Failed to fetch downloads')
        )
      })

      // Should retry and recover
      await waitFor(() => {
        expect(screen.getByText('model.bin')).toBeInTheDocument()
        expect(screen.getByText('45%')).toBeInTheDocument()
      })

      expect(callCount).toBe(2)
    })

    test('should resume download from interruption point', async () => {
      const mockApi = apiClient
      
      // Mock download state persistence
      mockLocalStorage.setItem.mockImplementation((key, value) => {
        if (key === 'download_states') {
          mockLocalStorage.store[key] = value
        }
      })

      mockLocalStorage.getItem.mockImplementation((key) => {
        if (key === 'download_states') {
          return JSON.stringify({
            'download_1': {
              id: 'download_1',
              progress: 30,
              downloaded: 300000000,
              interrupted_at: Date.now() - 5000,
              url: 'https://example.com/model.bin',
              filename: 'model.bin'
            }
          })
        }
        return mockLocalStorage.store[key]
      })

      mockApi.getDownloads.mockResolvedValue({
        downloads: [
          {
            id: 'download_1',
            status: 'paused',
            progress: 30,
            speed: 0,
            eta: 0,
            url: 'https://example.com/model.bin',
            filename: 'model.bin',
            size: 1000000000,
            downloaded: 300000000,
            error: 'Network interruption',
            retries: 0
          }
        ]
      })

      renderWithProviders(<DownloadDashboard />)
      
      await waitFor(() => {
        expect(screen.getByText('model.bin')).toBeInTheDocument()
        expect(screen.getByText('30%')).toBeInTheDocument()
      })

      // Test resume functionality
      mockApi.resumeDownload.mockResolvedValue({ success: true })
      
      const resumeButton = screen.getByRole('button', { name: /resume/i })
      await userEvent.click(resumeButton)

      await waitFor(() => {
        expect(mockApi.resumeDownload).toHaveBeenCalledWith('download_1')
        expect(toast.success).toHaveBeenCalledWith('Download resumed')
      })
    })

    test('should handle multiple concurrent download recoveries', async () => {
      const mockApi = apiClient
      
      mockApi.getDownloads.mockResolvedValue({
        downloads: [
          {
            id: 'download_1',
            status: 'downloading',
            progress: 25,
            speed: 1.5,
            eta: 300,
            url: 'https://example.com/model1.bin',
            filename: 'model1.bin',
            size: 500000000,
            downloaded: 125000000,
            error: null,
            retries: 2
          },
          {
            id: 'download_2',
            status: 'recovering',
            progress: 60,
            speed: 0,
            eta: 0,
            url: 'https://example.com/model2.bin',
            filename: 'model2.bin',
            size: 800000000,
            downloaded: 480000000,
            error: 'Connection timeout',
            retries: 1
          },
          {
            id: 'download_3',
            status: 'paused',
            progress: 80,
            speed: 0,
            eta: 0,
            url: 'https://example.com/model3.bin',
            filename: 'model3.bin',
            size: 200000000,
            downloaded: 160000000,
            error: 'Network error',
            retries: 3
          }
        ]
      })

      renderWithProviders(<DownloadDashboard />)
      
      await waitFor(() => {
        expect(screen.getByText('model1.bin')).toBeInTheDocument()
        expect(screen.getByText('model2.bin')).toBeInTheDocument()
        expect(screen.getByText('model3.bin')).toBeInTheDocument()
      })

      // Verify all downloads show recovery status
      expect(screen.getByText('25%')).toBeInTheDocument()
      expect(screen.getByText('60%')).toBeInTheDocument()
      expect(screen.getByText('80%')).toBeInTheDocument()
    })
  })

  describe('Circuit Breaker Recovery', () => {
    test('should activate circuit breaker after repeated failures', async () => {
      const mockApi = apiClient
      
      // Simulate repeated network failures
      mockApi.getDownloads.mockRejectedValue(new Error('Network unavailable'))
      
      renderWithProviders(<DownloadDashboard />)
      
      // Should show circuit breaker message after multiple failures
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringContaining('Circuit breaker activated')
        )
      })
    })

    test('should recover after circuit breaker timeout', async () => {
      const mockApi = apiClient
      
      let callCount = 0
      mockApi.getDownloads.mockImplementation(() => {
        callCount++
        if (callCount <= 3) {
          return Promise.reject(new Error('Service unavailable'))
        } else {
          return Promise.resolve({ downloads: [] })
        }
      })

      renderWithProviders(<DownloadDashboard />)
      
      // Wait for circuit breaker to activate and then recover
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 1000))
      })

      // Should eventually recover
      await waitFor(() => {
        expect(screen.getByText(/no downloads/i)).toBeInTheDocument()
      })
    })
  })
})

describe('Browser Refresh Recovery Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocalStorage.clear()
  })

  test('should restore UI state after browser refresh', async () => {
    const mockApi = apiClient
    
    // Simulate stored UI state
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'ui_state') {
        return JSON.stringify({
          activeTab: 'downloads',
          filters: {
            status: 'all',
            sortBy: 'date'
          },
          expandedItems: ['download_1', 'download_2']
        })
      }
      return null
    })

    mockApi.getDownloads.mockResolvedValue({
      downloads: [
        {
          id: 'download_1',
          status: 'completed',
          progress: 100,
          speed: 0,
          eta: 0,
          url: 'https://example.com/model1.bin',
          filename: 'model1.bin',
          size: 500000000,
          downloaded: 500000000,
          error: null,
          retries: 0
        }
      ]
    })

    renderWithProviders(<DownloadDashboard />)
    
    // Should restore UI state from localStorage
    await waitFor(() => {
      expect(screen.getByText('model1.bin')).toBeInTheDocument()
    })
  })

  test('should recover form data after browser refresh', async () => {
    const mockApi = apiClient
    
    // Simulate stored form data
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'form_data') {
        return JSON.stringify({
          workflowImport: {
            name: 'Test Workflow',
            description: 'A test workflow',
            url: 'https://example.com/workflow.json',
            selectedNodes: ['node1', 'node2']
          }
        })
      }
      return null
    })

    mockApi.getProjects.mockResolvedValue({ projects: [] })
    
    renderWithProviders(<ImportWorkflowUI />)
    
    // Should restore form data
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Workflow')).toBeInTheDocument()
      expect(screen.getByDisplayValue('https://example.com/workflow.json')).toBeInTheDocument()
    })
  })

  test('should recover WebSocket connection after refresh', async () => {
    const mockSocket = socket
    
    mockSocket.connect.mockImplementation(() => {
      setTimeout(() => {
        // Simulate reconnection event
        if (mockSocket.on.mock.calls.some(call => call[0] === 'reconnect')) {
          const reconnectHandler = mockSocket.on.mock.calls
            .find(call => call[0] === 'reconnect')?.[1]
          if (reconnectHandler) {
            reconnectHandler()
          }
        }
      }, 100)
    })

    renderWithProviders(<LiveLogViewer />)
    
    // Should attempt to reconnect
    expect(mockSocket.connect).toHaveBeenCalled()
    
    // Wait for reconnection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150))
    })
  })
})

describe('Model Manager Recovery Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocalStorage.clear()
  })

  test('should recover from model installation failure', async () => {
    const mockApi = apiClient
    
    mockApi.getModels.mockResolvedValue({
      models: [
        {
          id: 'model_1',
          name: 'Test Model',
          type: 'checkpoint',
          status: 'installing',
          progress: 45,
          error: null,
          retries: 1
        }
      ]
    })

    renderWithProviders(<ModelManager />)
    
    await waitFor(() => {
      expect(screen.getByText('Test Model')).toBeInTheDocument()
      expect(screen.getByText('45%')).toBeInTheDocument()
    })

    // Simulate recovery completion
    act(() => {
      // Update mock to show completed state
      mockApi.getModels.mockResolvedValue({
        models: [
          {
            id: 'model_1',
            name: 'Test Model',
            type: 'checkpoint',
            status: 'installed',
            progress: 100,
            error: null,
            retries: 2
          }
        ]
      })
    })

    // Should refresh and show completed state
    await waitFor(() => {
      expect(screen.getByText('installed')).toBeInTheDocument()
    })
  })

  test('should handle concurrent model installations with recovery', async () => {
    const mockApi = apiClient
    
    mockApi.getModels.mockResolvedValue({
      models: [
        {
          id: 'model_1',
          name: 'Model 1',
          type: 'checkpoint',
          status: 'installing',
          progress: 30,
          error: null,
          retries: 0
        },
        {
          id: 'model_2',
          name: 'Model 2',
          type: 'lora',
          status: 'recovering',
          progress: 65,
          error: 'Network timeout',
          retries: 2
        },
        {
          id: 'model_3',
          name: 'Model 3',
          type: 'embedding',
          status: 'installing',
          progress: 80,
          error: null,
          retries: 1
        }
      ]
    })

    renderWithProviders(<ModelManager />)
    
    await waitFor(() => {
      expect(screen.getByText('Model 1')).toBeInTheDocument()
      expect(screen.getByText('Model 2')).toBeInTheDocument()
      expect(screen.getByText('Model 3')).toBeInTheDocument()
    })

    // Verify all models show their respective states
    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
  })
})

describe('Workflow Import Recovery Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocalStorage.clear()
  })

  test('should recover workflow import after network failure', async () => {
    const mockApi = apiClient
    
    // Simulate stored import state
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'workflow_import_state') {
        return JSON.stringify({
          activeImport: {
            id: 'import_1',
            url: 'https://example.com/workflow.json',
            status: 'processing',
            progress: 40,
            error: null,
            retries: 1,
            timestamp: Date.now() - 30000
          }
        })
      }
      return null
    })

    mockApi.getProjects.mockResolvedValue({ projects: [] })
    
    renderWithProviders(<ImportWorkflowUI />)
    
    await waitFor(() => {
      expect(screen.getByText(/workflow import/i)).toBeInTheDocument()
    })

    // Should show recovery UI
    expect(screen.getByText(/resuming import/i)).toBeInTheDocument()
  })

  test('should handle workflow validation recovery', async () => {
    const mockApi = apiClient
    
    mockApi.importWorkflow.mockImplementation(() => {
      return Promise.reject(new Error('Workflow validation failed'))
    })

    mockApi.getProjects.mockResolvedValue({ projects: [] })
    
    renderWithProviders(<ImportWorkflowUI />)
    
    // Enter workflow URL
    const urlInput = screen.getByPlaceholderText(/enter workflow url/i)
    await userEvent.type(urlInput, 'https://example.com/invalid-workflow.json')
    
    const importButton = screen.getByRole('button', { name: /import/i })
    await userEvent.click(importButton)

    // Should show validation error
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        expect.stringContaining('validation failed')
      )
    })

    // Should provide recovery options
    expect(screen.getByText(/retry/i)).toBeInTheDocument()
  })
})

describe('Project Creation Recovery Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocalStorage.clear()
  })

  test('should recover project creation after server error', async () => {
    const mockApi = apiClient
    
    // Simulate stored project data
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'project_creation_state') {
        return JSON.stringify({
          formData: {
            name: 'Test Project',
            path: '/tmp/test-project',
            template: 'default',
            description: 'A test project'
          },
          step: 2,
          error: 'Server timeout',
          retries: 1
        })
      }
      return null
    })

    mockApi.getProjects.mockResolvedValue({ projects: [] })
    
    renderWithProviders(<NewWorkflowUI />)
    
    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })

    // Should show recovery UI
    expect(screen.getByText(/recovering project creation/i)).toBeInTheDocument()
  })

  test('should handle concurrent project operations', async () => {
    const mockApi = apiClient
    
    mockApi.getProjects.mockResolvedValue({
      projects: [
        {
          id: 'project_1',
          name: 'Project 1',
          status: 'creating',
          progress: 25,
          error: null
        },
        {
          id: 'project_2',
          name: 'Project 2',
          status: 'installing',
          progress: 60,
          error: null
        },
        {
          id: 'project_3',
          name: 'Project 3',
          status: 'recovering',
          progress: 80,
          error: 'Installation failed',
          retries: 2
        }
      ]
    })

    renderWithProviders(<NewWorkflowUI />)
    
    await waitFor(() => {
      expect(screen.getByText('Project 1')).toBeInTheDocument()
      expect(screen.getByText('Project 2')).toBeInTheDocument()
      expect(screen.getByText('Project 3')).toBeInTheDocument()
    })
  })
})

describe('WebSocket Recovery Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('should reconnect WebSocket after disconnection', async () => {
    const mockSocket = socket
    
    let connectionCount = 0
    mockSocket.connect.mockImplementation(() => {
      connectionCount++
      setTimeout(() => {
        if (connectionCount === 2) {
          // Simulate successful reconnection
          if (mockSocket.on.mock.calls.some(call => call[0] === 'connect')) {
            const connectHandler = mockSocket.on.mock.calls
              .find(call => call[0] === 'connect')?.[1]
            if (connectHandler) {
              connectHandler()
            }
          }
        }
      }, 100)
    })

    renderWithProviders(<LiveLogViewer />)
    
    // Should attempt initial connection
    expect(mockSocket.connect).toHaveBeenCalled()
    
    // Simulate disconnection
    act(() => {
      const disconnectHandler = mockSocket.on.mock.calls
        .find(call => call[0] === 'disconnect')?.[1]
      if (disconnectHandler) {
        disconnectHandler()
      }
    })

    // Should attempt reconnection
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150))
    })

    expect(mockSocket.connect).toHaveBeenCalledTimes(2)
  })

  test('should recover missed messages after reconnection', async () => {
    const mockSocket = socket
    const mockApi = apiClient
    
    mockApi.getLogs.mockResolvedValue({ logs: [] })
    
    // Store missed messages
    const missedMessages = [
      { event: 'log', data: { message: 'Log 1', timestamp: Date.now() - 10000 } },
      { event: 'log', data: { message: 'Log 2', timestamp: Date.now() - 5000 } }
    ]

    mockSocket.connect.mockImplementation(() => {
      setTimeout(() => {
        // Simulate reconnection with missed messages
        if (mockSocket.on.mock.calls.some(call => call[0] === 'reconnect')) {
          const reconnectHandler = mockSocket.on.mock.calls
            .find(call => call[0] === 'reconnect')?.[1]
          if (reconnectHandler) {
            reconnectHandler()
          }
        }
        
        // Deliver missed messages
        setTimeout(() => {
          missedMessages.forEach(msg => {
            const logHandler = mockSocket.on.mock.calls
              .find(call => call[0] === 'log')?.[1]
            if (logHandler) {
              logHandler(msg.data)
            }
          })
        }, 50)
      }, 100)
    })

    renderWithProviders(<LiveLogViewer />)
    
    // Wait for reconnection and message recovery
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200))
    })

    // Should show recovered messages
    expect(screen.getByText('Log 1')).toBeInTheDocument()
    expect(screen.getByText('Log 2')).toBeInTheDocument()
  })
})

describe('Performance and Load Tests', () => {
  test('should handle rapid UI state changes without errors', async () => {
    const mockApi = apiClient
    
    mockApi.getDownloads.mockResolvedValue({ downloads: [] })
    
    renderWithProviders(<DownloadDashboard />)
    
    // Simulate rapid state changes
    for (let i = 0; i < 10; i++) {
      act(() => {
        mockLocalStorage.setItem('ui_state', JSON.stringify({
          activeTab: i % 2 === 0 ? 'downloads' : 'settings',
          lastUpdate: Date.now()
        }))
      })
    }

    // Should not crash or show errors
    expect(screen.getByText(/downloads/i)).toBeInTheDocument()
  })

  test('should recover from memory pressure scenarios', async () => {
    const mockApi = apiClient
    
    // Simulate large dataset
    const largeDownloadList = Array.from({ length: 100 }, (_, i) => ({
      id: `download_${i}`,
      status: i % 4 === 0 ? 'downloading' : i % 4 === 1 ? 'paused' : i % 4 === 2 ? 'completed' : 'failed',
      progress: Math.floor(Math.random() * 100),
      speed: Math.random() * 10,
      eta: Math.floor(Math.random() * 1000),
      url: `https://example.com/model${i}.bin`,
      filename: `model${i}.bin`,
      size: Math.floor(Math.random() * 1000000000),
      downloaded: Math.floor(Math.random() * 1000000000),
      error: i % 4 === 3 ? 'Network error' : null,
      retries: Math.floor(Math.random() * 3)
    }))

    mockApi.getDownloads.mockResolvedValue({ downloads: largeDownloadList })
    
    renderWithProviders(<DownloadDashboard />)
    
    // Should handle large dataset without crashing
    await waitFor(() => {
      expect(screen.getByText(/downloads/i)).toBeInTheDocument()
    })

    // Should be able to interact with UI
    const settingsButton = screen.getByRole('button', { name: /settings/i })
    await userEvent.click(settingsButton)
    
    expect(screen.getByText(/download settings/i)).toBeInTheDocument()
  })
})

describe('Error Recovery Integration Tests', () => {
  test('should provide graceful error recovery for all components', async () => {
    const mockApi = apiClient
    
    // Simulate cascading failures
    mockApi.getDownloads.mockRejectedValue(new Error('Service unavailable'))
    mockApi.getDownloadSettings.mockRejectedValue(new Error('Settings service down'))
    mockApi.getModels.mockRejectedValue(new Error('Model service unavailable'))
    
    renderWithProviders(<DownloadDashboard />)
    
    // Should show error states gracefully
    await waitFor(() => {
      expect(screen.getByText(/unable to load downloads/i)).toBeInTheDocument()
    })

    // Should provide retry options
    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).toBeInTheDocument()
  })

  test('should maintain user experience during recovery operations', async () => {
    const mockApi = apiClient
    
    let isRecovering = true
    
    mockApi.getDownloads.mockImplementation(() => {
      if (isRecovering) {
        return Promise.reject(new Error('Recovering...'))
      } else {
        return Promise.resolve({ downloads: [] })
      }
    })

    renderWithProviders(<DownloadDashboard />)
    
    // Should show loading/recovery state
    await waitFor(() => {
      expect(screen.getByText(/recovering/i)).toBeInTheDocument()
    })

    // Simulate recovery completion
    isRecovering = false
    
    // Should refresh and show normal state
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 1000))
    })

    expect(screen.getByText(/no downloads/i)).toBeInTheDocument()
  })
})

// Export test utilities for other test files
export const recoveryTestUtils = {
  mockLocalStorage,
  mockIndexedDB,
  renderWithProviders,
  createTestQueryClient,
  simulateNetworkFailure: (duration = 1000) => {
    return new Promise(resolve => setTimeout(resolve, duration))
  },
  simulateBrowserRefresh: () => {
    // Clear and recreate localStorage to simulate refresh
    mockLocalStorage.clear()
    window.dispatchEvent(new Event('beforeunload'))
    window.dispatchEvent(new Event('load'))
  }
}