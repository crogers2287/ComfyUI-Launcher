import { useState, useEffect } from 'react'
import { X, RefreshCw, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Progress } from './ui/progress'
import { Card, CardContent } from './ui/card'
import { 
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from './ui/collapsible'
import type { RecoveryStatus, RecoveryState } from '@/lib/types'

interface RecoveryBannerProps {
  recoveryOperations: RecoveryStatus[]
  onDismiss?: () => void
  className?: string
}

export function RecoveryBanner({ recoveryOperations, onDismiss, className }: RecoveryBannerProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [dismissedOperations, setDismissedOperations] = useState<Set<string>>(new Set())

  // Filter out dismissed operations and completed ones after a delay
  const activeOperations = recoveryOperations.filter(op => 
    !dismissedOperations.has(op.operation_id) && 
    (op.state === 'recovering' || op.state === 'in_progress' || op.state === 'pending')
  )

  const completedOperations = recoveryOperations.filter(op =>
    !dismissedOperations.has(op.operation_id) &&
    (op.state === 'success' || op.state === 'failed' || op.state === 'exhausted')
  )

  // Auto-dismiss completed operations after 5 seconds
  useEffect(() => {
    completedOperations.forEach(op => {
      const timer = setTimeout(() => {
        setDismissedOperations(prev => new Set([...prev, op.operation_id]))
      }, 5000)
      
      return () => clearTimeout(timer)
    })
  }, [completedOperations])

  const allOperations = [...activeOperations, ...completedOperations]

  if (allOperations.length === 0) {
    return null
  }

  const getStateIcon = (state: RecoveryState) => {
    switch (state) {
      case 'recovering':
      case 'in_progress':
        return <RefreshCw className="h-4 w-4 animate-spin" />
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
      case 'exhausted':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'pending':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      default:
        return null
    }
  }

  const getStateBadgeVariant = (state: RecoveryState) => {
    switch (state) {
      case 'recovering':
      case 'in_progress':
        return 'default'
      case 'success':
        return 'secondary'
      case 'failed':
      case 'exhausted':
        return 'destructive'
      case 'pending':
        return 'outline'
      default:
        return 'outline'
    }
  }

  const formatTimeRemaining = (operation: RecoveryStatus) => {
    if (!operation.estimated_completion) return null
    
    const completionTime = new Date(operation.estimated_completion)
    const now = new Date()
    const diffMs = completionTime.getTime() - now.getTime()
    
    if (diffMs <= 0) return 'Almost done...'
    
    const minutes = Math.ceil(diffMs / 60000)
    if (minutes < 60) return `~${minutes}min remaining`
    
    const hours = Math.ceil(minutes / 60)
    return `~${hours}h remaining`
  }

  const dismissOperation = (operationId: string) => {
    setDismissedOperations(prev => new Set([...prev, operationId]))
  }

  const dismissAllCompleted = () => {
    const completedIds = completedOperations.map(op => op.operation_id)
    setDismissedOperations(prev => new Set([...prev, ...completedIds]))
  }

  return (
    <Card className={`border-l-4 border-l-blue-500 ${className}`}>
      <CardContent className="p-4">
        <Collapsible open={!isCollapsed} onOpenChange={setIsCollapsed}>
          <div className="flex items-center justify-between">
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="p-0 h-auto">
                <div className="flex items-center gap-2">
                  <RefreshCw className={`h-5 w-5 ${activeOperations.length > 0 ? 'animate-spin' : ''}`} />
                  <span className="font-medium">
                    Recovery Operations ({allOperations.length})
                  </span>
                </div>
              </Button>
            </CollapsibleTrigger>
            
            <div className="flex items-center gap-2">
              {completedOperations.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={dismissAllCompleted}
                  className="text-xs"
                >
                  Clear completed
                </Button>
              )}
              {onDismiss && (
                <Button variant="ghost" size="sm" onClick={onDismiss}>
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>

          <CollapsibleContent className="space-y-3 mt-4">
            {allOperations.map((operation) => (
              <div key={operation.operation_id} className="border rounded-lg p-3 bg-muted/30">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      {getStateIcon(operation.state)}
                      <span className="font-medium truncate">
                        {operation.operation_name}
                      </span>
                      <Badge variant={getStateBadgeVariant(operation.state)}>
                        {operation.state}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        Attempt {operation.attempt}/{operation.max_attempts}
                      </Badge>
                    </div>

                    {operation.progress !== undefined && (
                      <div className="space-y-1 mb-2">
                        <div className="flex justify-between text-sm text-muted-foreground">
                          <span>Progress</span>
                          <span>{Math.round(operation.progress * 100)}%</span>
                        </div>
                        <Progress value={operation.progress * 100} className="h-2" />
                      </div>
                    )}

                    {operation.error && (
                      <div className="text-sm text-red-600 bg-red-50 dark:bg-red-950 p-2 rounded mt-2">
                        <span className="font-medium">Error:</span> {operation.error}
                      </div>
                    )}

                    <div className="flex items-center justify-between text-xs text-muted-foreground mt-2">
                      <span>
                        Started: {new Date(operation.started_at).toLocaleTimeString()}
                      </span>
                      {formatTimeRemaining(operation) && (
                        <span>{formatTimeRemaining(operation)}</span>
                      )}
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => dismissOperation(operation.operation_id)}
                    className="ml-2"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}

            {allOperations.length === 0 && (
              <div className="text-center text-muted-foreground py-4">
                No active recovery operations
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  )
}

export default RecoveryBanner