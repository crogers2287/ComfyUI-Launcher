import { useState, useEffect, useRef } from 'react'
import { ScrollArea } from './ui/scroll-area'
import { Button } from './ui/button'
import { FileTextIcon, RefreshCwIcon, DownloadIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'
import { subscribeToProjectLogs, LogEvent } from '@/lib/socket'

interface LogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
}

interface LogsViewerProps {
  projectId: string
  className?: string
}

export function LogsViewer({ projectId, className }: LogsViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getProjectLogs(projectId, {
        per_page: 100,
      })
      setLogs(response.logs)
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    
    // Subscribe to live logs via WebSocket
    const unsubscribe = subscribeToProjectLogs(projectId, (log: LogEvent) => {
      setLogs(prev => [...prev, {
        timestamp: log.timestamp,
        level: log.level?.toLowerCase() as 'info' | 'warn' | 'error' | 'debug' || 'info',
        message: log.message
      }])
      
      // Auto-scroll to bottom when new logs arrive
      if (scrollAreaRef.current) {
        const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
        if (scrollContainer) {
          scrollContainer.scrollTop = scrollContainer.scrollHeight
        }
      }
    })
    
    return () => {
      unsubscribe()
    }
  }, [projectId])

  const downloadLogs = () => {
    const logsText = logs.map(log => 
      `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}`
    ).join('\\n')
    
    const blob = new Blob([logsText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `project-${projectId}-logs.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <FileTextIcon className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-medium">Installation Logs</h3>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={fetchLogs}
            disabled={isLoading}
            className="h-8 w-8"
          >
            <RefreshCwIcon className={cn(
              "h-4 w-4",
              isLoading && "animate-spin"
            )} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={downloadLogs}
            className="h-8 w-8"
          >
            <DownloadIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      <ScrollArea ref={scrollAreaRef} className="flex-1 p-3">
        <div className="space-y-1 font-mono text-xs">
          {logs.length === 0 ? (
            <div className="text-muted-foreground text-center py-8">
              No logs available
            </div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="flex gap-2">
                <span className="text-muted-foreground">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={cn(
                  "font-semibold",
                  log.level === 'info' && "text-blue-600 dark:text-blue-400",
                  log.level === 'warn' && "text-yellow-600 dark:text-yellow-400",
                  log.level === 'error' && "text-red-600 dark:text-red-400"
                )}>
                  [{log.level.toUpperCase()}]
                </span>
                <span className="text-foreground">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  )
}