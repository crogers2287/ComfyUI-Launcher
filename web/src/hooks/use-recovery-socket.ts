import { useEffect, useState, useCallback, useRef } from 'react'
import { getSocket } from '@/lib/socket'
import type { 
  RecoveryStatus, 
  ProjectRecoveryInfo, 
  DownloadRecoveryStatus
} from '@/lib/types'

// Recovery event handlers
type RecoveryEventHandlers = {
  onRecoveryStarted?: (status: RecoveryStatus) => void
  onRecoveryProgress?: (status: RecoveryStatus & { progress: number }) => void
  onRecoveryCompleted?: (status: RecoveryStatus) => void
  onRecoveryFailed?: (status: RecoveryStatus & { error: string }) => void
  onDownloadRecovery?: (status: DownloadRecoveryStatus) => void
}

export function useRecoverySocket(projectId?: string, handlers: RecoveryEventHandlers = {}) {
  const [recoveryOperations, setRecoveryOperations] = useState<RecoveryStatus[]>([])
  const [projectRecoveryInfo, setProjectRecoveryInfo] = useState<ProjectRecoveryInfo | null>(null)
  const [downloadStatuses, setDownloadStatuses] = useState<Map<string, DownloadRecoveryStatus>>(new Map())
  
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  // Update recovery operations
  const updateRecoveryOperation = useCallback((status: RecoveryStatus) => {
    setRecoveryOperations(prev => {
      const existing = prev.find(op => op.operation_id === status.operation_id)
      if (existing) {
        return prev.map(op => 
          op.operation_id === status.operation_id ? { ...op, ...status } : op
        )
      } else {
        return [...prev, status]
      }
    })

    // Update project recovery info
    if (projectId && status.operation_id.includes(projectId)) {
      setProjectRecoveryInfo(prev => {
        const activeOps = recoveryOperations.filter(op => 
          op.state === 'recovering' || op.state === 'in_progress'
        )
        return {
          project_id: projectId,
          active_operations: activeOps,
          total_attempts: (prev?.total_attempts || 0) + 1,
          last_recovery_at: status.updated_at
        }
      })
    }
  }, [projectId, recoveryOperations])

  // Remove completed/failed operations after delay
  useEffect(() => {
    const completedOps = recoveryOperations.filter(op => 
      op.state === 'success' || op.state === 'failed' || op.state === 'exhausted'
    )

    if (completedOps.length > 0) {
      const timer = setTimeout(() => {
        setRecoveryOperations(prev => 
          prev.filter(op => 
            op.state !== 'success' && op.state !== 'failed' && op.state !== 'exhausted'
          )
        )
      }, 10000) // Remove after 10 seconds

      return () => clearTimeout(timer)
    }
  }, [recoveryOperations])

  useEffect(() => {
    const socket = getSocket()

    // Recovery event listeners
    const onRecoveryStarted = (status: RecoveryStatus) => {
      updateRecoveryOperation(status)
      handlersRef.current.onRecoveryStarted?.(status)
    }

    const onRecoveryProgress = (status: RecoveryStatus & { progress: number }) => {
      updateRecoveryOperation(status)
      handlersRef.current.onRecoveryProgress?.(status)
    }

    const onRecoveryCompleted = (status: RecoveryStatus) => {
      updateRecoveryOperation({ ...status, state: 'success' })
      handlersRef.current.onRecoveryCompleted?.(status)
    }

    const onRecoveryFailed = (status: RecoveryStatus & { error: string }) => {
      updateRecoveryOperation({ ...status, state: 'failed' })
      handlersRef.current.onRecoveryFailed?.(status)
    }

    const onDownloadRecovery = (status: DownloadRecoveryStatus) => {
      setDownloadStatuses(prev => new Map(prev.set(status.url, status)))
      handlersRef.current.onDownloadRecovery?.(status)
    }

    // Subscribe to recovery events
    socket.on('recovery_started', onRecoveryStarted)
    socket.on('recovery_progress', onRecoveryProgress)  
    socket.on('recovery_completed', onRecoveryCompleted)
    socket.on('recovery_failed', onRecoveryFailed)
    socket.on('download_recovery', onDownloadRecovery)

    // Join project room if specified
    if (projectId) {
      socket.emit('join_recovery_room', projectId)
    }

    // Subscribe to general recovery events
    socket.emit('subscribe_recovery')

    // Cleanup
    return () => {
      socket.off('recovery_started', onRecoveryStarted)
      socket.off('recovery_progress', onRecoveryProgress)
      socket.off('recovery_completed', onRecoveryCompleted)
      socket.off('recovery_failed', onRecoveryFailed)  
      socket.off('download_recovery', onDownloadRecovery)
      
      if (projectId) {
        socket.emit('leave_recovery_room', projectId)
      }
      socket.emit('unsubscribe_recovery')
    }
  }, [projectId, updateRecoveryOperation])

  // API functions
  const pauseRecovery = useCallback(async (operationId: string) => {
    try {
      const response = await fetch(`/api/recovery/${operationId}/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      return await response.json()
    } catch (error) {
      console.error('Failed to pause recovery:', error)
      throw error
    }
  }, [])

  const resumeRecovery = useCallback(async (operationId: string) => {
    try {
      const response = await fetch(`/api/recovery/${operationId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      return await response.json()
    } catch (error) {
      console.error('Failed to resume recovery:', error)
      throw error
    }
  }, [])

  const cancelRecovery = useCallback(async (operationId: string) => {
    try {
      const response = await fetch(`/api/recovery/${operationId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      return await response.json()
    } catch (error) {
      console.error('Failed to cancel recovery:', error)
      throw error
    }
  }, [])

  const getRecoveryStatus = useCallback(async (operationId: string) => {
    try {
      const response = await fetch(`/api/recovery/${operationId}/status`)
      return await response.json()
    } catch (error) {
      console.error('Failed to get recovery status:', error)
      throw error
    }
  }, [])

  return {
    // State
    recoveryOperations,
    projectRecoveryInfo,
    downloadStatuses: Array.from(downloadStatuses.values()),
    
    // Computed state
    hasActiveRecovery: recoveryOperations.some(op => 
      op.state === 'recovering' || op.state === 'in_progress'
    ),
    
    // API functions
    pauseRecovery,
    resumeRecovery, 
    cancelRecovery,
    getRecoveryStatus,
    
    // Utilities
    getDownloadStatus: (url: string) => downloadStatuses.get(url),
    clearCompletedOperations: () => setRecoveryOperations(prev =>
      prev.filter(op => op.state === 'recovering' || op.state === 'in_progress')
    )
  }
}

// Hook specifically for global recovery state (across all projects)
export function useGlobalRecovery() {
  return useRecoverySocket(undefined, {
    onRecoveryStarted: (status) => {
      console.log('Global recovery started:', status.operation_name)
    },
    onRecoveryCompleted: (status) => {
      console.log('Global recovery completed:', status.operation_name)
    },
    onRecoveryFailed: (status) => {
      console.error('Global recovery failed:', status.operation_name, status.error)
    }
  })
}

// Hook for project-specific recovery
export function useProjectRecovery(projectId: string) {
  return useRecoverySocket(projectId, {
    onDownloadRecovery: (status) => {
      console.log(`Download recovery for project ${projectId}:`, status)
    }
  })
}