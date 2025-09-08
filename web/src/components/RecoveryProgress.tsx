import * as React from "react"
import { RefreshCw, Download, Pause, Play, AlertTriangle, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "./ui/badge"
import { Button } from "./ui/button"
import type { DownloadRecoveryStatus } from "@/lib/types"

interface RecoveryProgressProps {
  // Basic progress props
  value?: number
  
  // Recovery-specific props  
  recoveryStatus?: DownloadRecoveryStatus
  showRetryIndicator?: boolean
  showSpeedInfo?: boolean
  onPause?: () => void
  onResume?: () => void
  onCancel?: () => void
  
  // Visual customization
  variant?: 'default' | 'recovery' | 'error' | 'success'
  className?: string
}

const RecoveryProgress = React.forwardRef<
  HTMLDivElement,
  RecoveryProgressProps
>(({ 
  className, 
  value, 
  recoveryStatus,
  showRetryIndicator = true,
  showSpeedInfo = true,
  onPause,
  onResume,
  onCancel,
  variant = 'default',
  ...props 
}, ref) => {
  const progressValue = recoveryStatus?.progress ?? value ?? 0
  const isRecovering = recoveryStatus?.status === 'recovering' || (recoveryStatus?.attempts && recoveryStatus.attempts > 1)
  const isDownloading = recoveryStatus?.status === 'downloading'
  const isPaused = recoveryStatus?.status === 'pending'
  const isCompleted = recoveryStatus?.status === 'completed'
  const isFailed = recoveryStatus?.status === 'failed'

  // Calculate visual variant
  const effectiveVariant = variant === 'default' && recoveryStatus 
    ? (isRecovering ? 'recovery' : isFailed ? 'error' : isCompleted ? 'success' : 'default')
    : variant

  // Format bytes to human readable
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  // Format speed
  const formatSpeed = (bps: number) => {
    return formatBytes(bps) + '/s'
  }

  // Get progress bar color based on state
  const getProgressColor = () => {
    switch (effectiveVariant) {
      case 'recovery':
        return 'bg-blue-500'
      case 'error':
        return 'bg-red-500'
      case 'success':
        return 'bg-green-500'
      default:
        return 'bg-primary'
    }
  }

  // Get status icon
  const getStatusIcon = () => {
    if (isRecovering) {
      return <RefreshCw className="h-3 w-3 animate-spin" />
    }
    if (isDownloading) {
      return <Download className="h-3 w-3" />
    }
    if (isPaused) {
      return <Pause className="h-3 w-3" />
    }
    if (isCompleted) {
      return <CheckCircle className="h-3 w-3 text-green-500" />
    }
    if (isFailed) {
      return <AlertTriangle className="h-3 w-3 text-red-500" />
    }
    return null
  }

  return (
    <div className="space-y-2">
      {/* Progress info header */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="font-medium">
            {isRecovering && 'Recovering'}
            {isDownloading && !isRecovering && 'Downloading'}
            {isPaused && 'Paused'}
            {isCompleted && 'Completed'}
            {isFailed && 'Failed'}
          </span>
          
          {/* Retry indicator */}
          {showRetryIndicator && recoveryStatus && recoveryStatus.attempts > 1 && (
            <Badge 
              variant={isRecovering ? "default" : "secondary"} 
              className="text-xs flex items-center gap-1"
            >
              <RefreshCw className={cn("h-2 w-2", isRecovering && "animate-spin")} />
              Attempt {recoveryStatus.attempts}
            </Badge>
          )}
        </div>

        {/* Progress percentage */}
        <div className="flex items-center gap-2 text-muted-foreground">
          {recoveryStatus && showSpeedInfo && recoveryStatus.speed_bps && recoveryStatus.speed_bps > 0 && (
            <span className="text-xs">
              {formatSpeed(recoveryStatus.speed_bps)}
            </span>
          )}
          <span>{Math.round(progressValue * 100)}%</span>
        </div>
      </div>

      {/* Progress bar */}
      <div
        ref={ref}
        className={cn(
          "relative h-3 w-full overflow-hidden rounded-full bg-secondary",
          effectiveVariant === 'recovery' && "ring-2 ring-blue-200 dark:ring-blue-800",
          className
        )}
        {...props}
      >
        <div
          className={cn(
            "h-full flex-1 transition-all duration-500",
            getProgressColor(),
            // Add stripes animation for recovery
            isRecovering && "bg-gradient-to-r from-blue-500 to-blue-600 bg-[length:20px_20px] animate-pulse"
          )}
          style={{ transform: `translateX(-${100 - (progressValue * 100)}%)`, width: `${progressValue * 100}%` }}
        />
        
        {/* Resume point indicator for partial downloads */}
        {recoveryStatus && recoveryStatus.bytes_downloaded > 0 && recoveryStatus.total_bytes > 0 && (
          <div
            className="absolute top-0 h-full w-0.5 bg-yellow-400"
            style={{
              left: `${(recoveryStatus.bytes_downloaded / recoveryStatus.total_bytes) * 100}%`
            }}
            title="Resume point"
          />
        )}
      </div>

      {/* Download details */}
      {recoveryStatus && (recoveryStatus.bytes_downloaded > 0 || recoveryStatus.total_bytes > 0) && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {formatBytes(recoveryStatus.bytes_downloaded)} 
            {recoveryStatus.total_bytes > 0 && ` / ${formatBytes(recoveryStatus.total_bytes)}`}
          </span>
          
          {/* Action buttons */}
          <div className="flex gap-1">
            {(isDownloading || isRecovering) && onPause && (
              <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={onPause}>
                <Pause className="h-3 w-3" />
              </Button>
            )}
            {isPaused && onResume && (
              <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={onResume}>
                <Play className="h-3 w-3" />
              </Button>
            )}
            {onCancel && (
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-5 w-5 p-0 hover:text-destructive" 
                onClick={onCancel}
              >
                ×
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Error message */}
      {recoveryStatus && recoveryStatus.error && (
        <div className="text-xs text-destructive bg-destructive/10 p-2 rounded">
          {recoveryStatus.error}
        </div>
      )}
    </div>
  )
})

RecoveryProgress.displayName = "RecoveryProgress"

export { RecoveryProgress }