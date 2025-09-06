import { io, Socket } from 'socket.io-client'

// WebSocket connection singleton
let socket: Socket | null = null

export const getSocket = (): Socket => {
  if (!socket) {
    // Connect to the backend WebSocket server
    socket = io('/', {
      path: '/socket.io/',
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    socket.on('connect', () => {
      console.log('WebSocket connected')
    })

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
    })

    socket.on('error', (error) => {
      console.error('WebSocket error:', error)
    })
  }

  return socket
}

// Progress event types
export interface ProgressEvent {
  task_id: string
  project_id: string
  type: 'download' | 'install' | 'validation' | 'general'
  status: 'started' | 'progress' | 'completed' | 'failed'
  message: string
  progress?: number
  total?: number
  current?: number
  details?: any
}

// Subscribe to progress events
export const subscribeToProgress = (
  projectId: string,
  callback: (progress: ProgressEvent) => void
) => {
  const socket = getSocket()
  
  // Join the project room
  socket.emit('join_project', projectId)
  
  // Listen for progress events
  socket.on('progress', callback)
  
  // Return cleanup function
  return () => {
    socket.emit('leave_project', projectId)
    socket.off('progress', callback)
  }
}

// Subscribe to logs
export interface LogEvent {
  message: string
  timestamp: string
  level?: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
  type: 'server' | 'install' | 'project'
}

export const subscribeToLogs = (
  logType: 'server' | 'install' | 'project' = 'server',
  projectId?: string,
  callback?: (log: LogEvent) => void
) => {
  const socket = getSocket()
  
  // Subscribe to logs with the new endpoint structure
  socket.emit('subscribe_logs', { 
    log_type: logType, 
    project_id: projectId 
  })
  
  // Handle log entries
  if (callback) {
    socket.on('log_entry', callback)
  }
  
  // Handle subscription events
  socket.on('log_subscribed', (data) => {
    console.log('Subscribed to logs:', data)
  })
  
  socket.on('log_error', (error) => {
    console.error('Log subscription error:', error)
  })
  
  return () => {
    socket.emit('unsubscribe_logs', { 
      log_type: logType, 
      project_id: projectId 
    })
    if (callback) {
      socket.off('log_entry', callback)
    }
    socket.off('log_subscribed')
    socket.off('log_error')
  }
}

// Legacy function for project-specific logs
export const subscribeToProjectLogs = (
  projectId: string,
  callback: (log: LogEvent) => void
) => {
  return subscribeToLogs('project', projectId, callback)
}