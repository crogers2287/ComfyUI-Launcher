import { useState, useEffect, useRef } from 'react'
import { ScrollArea } from './ui/scroll-area'
import { Button } from './ui/button'
import { Card, CardContent } from './ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible'
import { 
  FileText, 
  ChevronDown, 
  ChevronUp, 
  Download,
  Server,
  HardDrive
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { subscribeToLogs, LogEvent } from '@/lib/socket'

interface LiveLogViewerProps {
  className?: string
  defaultOpen?: boolean
  maxHeight?: string
}

export function LiveLogViewer({ 
  className, 
  defaultOpen = false,
  maxHeight = "400px"
}: LiveLogViewerProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  const [logs, setLogs] = useState<LogEvent[]>([])
  const [logType, setLogType] = useState<'server' | 'install'>('server')
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const [isConnected, setIsConnected] = useState(false)

  // Auto-scroll to bottom when new logs arrive
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }

  useEffect(() => {
    if (!isOpen) return

    // Subscribe to logs
    const unsubscribe = subscribeToLogs(logType, undefined, (log: LogEvent) => {
      setLogs(prev => {
        const newLogs = [...prev, log]
        // Keep only last 500 logs to prevent memory issues
        if (newLogs.length > 500) {
          return newLogs.slice(-500)
        }
        return newLogs
      })
      
      // Auto-scroll to bottom
      setTimeout(scrollToBottom, 10)
    })

    setIsConnected(true)
    
    return () => {
      unsubscribe()
      setIsConnected(false)
    }
  }, [isOpen, logType])

  const clearLogs = () => {
    setLogs([])
  }

  const downloadLogs = () => {
    const logsText = logs.map(log => 
      `[${log.timestamp}] [${log.level || 'INFO'}] ${log.message}`
    ).join('\n')
    
    const blob = new Blob([logsText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${logType}-logs-${new Date().toISOString().split('T')[0]}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const getLogIcon = () => {
    if (logType === 'server') return <Server className="h-4 w-4" />
    if (logType === 'install') return <HardDrive className="h-4 w-4" />
    return <FileText className="h-4 w-4" />
  }

  const getLogTypeLabel = () => {
    if (logType === 'server') return 'Server Logs'
    if (logType === 'install') return 'Installation Logs'
    return 'Logs'
  }

  return (
    <div className={cn("w-full", className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <Card>
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-2">
                {getLogIcon()}
                <h3 className="text-sm font-medium">{getLogTypeLabel()}</h3>
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  isConnected ? "bg-green-500" : "bg-gray-400"
                )} />
                {logs.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    ({logs.length} entries)
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center rounded-md border">
                  <Button
                    variant={logType === 'server' ? 'default' : 'ghost'}
                    size="sm"
                    className="h-7 px-2 text-xs rounded-r-none"
                    onClick={(e) => {
                      e.stopPropagation()
                      setLogType('server')
                    }}
                  >
                    Server
                  </Button>
                  <Button
                    variant={logType === 'install' ? 'default' : 'ghost'}
                    size="sm"
                    className="h-7 px-2 text-xs rounded-l-none"
                    onClick={(e) => {
                      e.stopPropagation()
                      setLogType('install')
                    }}
                  >
                    Install
                  </Button>
                </div>
                {isOpen ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </div>
          </CollapsibleTrigger>
          
          <CollapsibleContent>
            <div className="border-t">
              <div className="flex items-center justify-between p-3 border-b bg-muted/20">
                <div className="text-xs text-muted-foreground">
                  Live streaming {getLogTypeLabel().toLowerCase()}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearLogs}
                    className="h-7 px-2 text-xs"
                  >
                    Clear
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={downloadLogs}
                    disabled={logs.length === 0}
                    className="h-7 px-2 text-xs"
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Download
                  </Button>
                </div>
              </div>
              
              <CardContent className="p-0">
                <ScrollArea 
                  ref={scrollAreaRef} 
                  style={{ maxHeight }}
                  className="w-full"
                >
                  <div className="p-3 space-y-1 font-mono text-xs">
                    {logs.length === 0 ? (
                      <div className="text-muted-foreground text-center py-8">
                        {isConnected ? 'Waiting for log entries...' : 'Connecting to log stream...'}
                      </div>
                    ) : (
                      logs.map((log, index) => (
                        <div key={index} className="flex gap-2 text-xs leading-relaxed">
                          <span className="text-muted-foreground shrink-0 w-20">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                          {log.level && (
                            <span className={cn(
                              "font-semibold shrink-0 w-12",
                              log.level === 'INFO' && "text-blue-600 dark:text-blue-400",
                              log.level === 'WARN' && "text-yellow-600 dark:text-yellow-400", 
                              log.level === 'ERROR' && "text-red-600 dark:text-red-400"
                            )}>
                              [{log.level}]
                            </span>
                          )}
                          <span className="text-foreground break-all">
                            {log.message}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </div>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    </div>
  )
}