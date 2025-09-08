import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Badge } from './ui/badge'
import { Progress } from './ui/progress'
import { 
  DownloadIcon, 
  PauseIcon, 
  PlayIcon as ResumeIcon, 
  XIcon,
  SettingsIcon,
  RefreshCwIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ZapIcon,
  DatabaseIcon,
  TimerIcon
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'
import { toast } from 'sonner'
import type { DownloadSettings, DownloadStatus } from '@/lib/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'

interface DownloadDashboardProps {
  className?: string
}

const statusColors: Record<DownloadStatus, string> = {
  pending: 'bg-yellow-500',
  downloading: 'bg-blue-500',
  paused: 'bg-orange-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500'
}

const statusIcons: Record<DownloadStatus, React.ComponentType<any>> = {
  pending: ClockIcon,
  downloading: DownloadIcon,
  paused: ResumeIcon,
  completed: CheckCircleIcon,
  failed: XCircleIcon,
  cancelled: XIcon
}

export function DownloadDashboard({ className }: DownloadDashboardProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settings, setSettings] = useState<DownloadSettings | null>(null)
  const queryClient = useQueryClient()

  const downloadsQuery = useQuery({
    queryKey: ['downloads'],
    queryFn: async () => {
      const response = await apiClient.getDownloads()
      return response.downloads
    },
    refetchInterval: 2000, // Refresh every 2 seconds
  })

  useQuery({
    queryKey: ['download-settings'],
    queryFn: async () => {
      const response = await apiClient.getDownloadSettings()
      setSettings(response.settings)
      return response.settings
    }
  })

  const pauseMutation = useMutation({
    mutationFn: apiClient.pauseDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] })
      toast.success('Download paused')
    },
    onError: (error) => {
      toast.error(`Failed to pause download: ${error.message}`)
    }
  })

  const resumeMutation = useMutation({
    mutationFn: apiClient.resumeDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] })
      toast.success('Download resumed')
    },
    onError: (error) => {
      toast.error(`Failed to resume download: ${error.message}`)
    }
  })

  const cancelMutation = useMutation({
    mutationFn: apiClient.cancelDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] })
      toast.success('Download cancelled')
    },
    onError: (error) => {
      toast.error(`Failed to cancel download: ${error.message}`)
    }
  })

  const updateSettingsMutation = useMutation({
    mutationFn: apiClient.updateDownloadSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['download-settings'] })
      toast.success('Settings updated')
      setIsSettingsOpen(false)
    },
    onError: (error) => {
      toast.error(`Failed to update settings: ${error.message}`)
    }
  })

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatSpeed = (bytesPerSecond: number): string => {
    return formatBytes(bytesPerSecond) + '/s'
  }

  const formatTime = (seconds: number): string => {
    if (seconds === 0) return '0s'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${remainingSeconds}s`
    } else if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`
    } else {
      return `${remainingSeconds}s`
    }
  }

  const getStatusBadge = (status: DownloadStatus) => {
    const Icon = statusIcons[status]
    return (
      <Badge variant="secondary" className={cn('flex items-center gap-1', statusColors[status])}>
        <Icon {...({ className: "w-3 h-3" } as any)} />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    )
  }

  const handleSettingsUpdate = (newSettings: Partial<DownloadSettings>) => {
    if (!settings) return
    
    const updatedSettings = { ...settings, ...newSettings }
    setSettings(updatedSettings)
    updateSettingsMutation.mutate(updatedSettings)
  }

  const downloads = downloadsQuery.data || []
  const activeDownloads = downloads.filter(d => d.status === 'downloading' || d.status === 'paused')
  const completedDownloads = downloads.filter(d => d.status === 'completed')
  const failedDownloads = downloads.filter(d => d.status === 'failed')

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Download Manager</h2>
          <p className="text-muted-foreground">
            Manage your model downloads with pause, resume, and recovery capabilities
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadsQuery.refetch()}
            disabled={downloadsQuery.isFetching}
          >
            <RefreshCwIcon className={cn('w-4 h-4 mr-2', downloadsQuery.isFetching && 'animate-spin')} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSettingsOpen(true)}
          >
            <SettingsIcon className="w-4 h-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Downloads</CardTitle>
            <DatabaseIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{downloads.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
            <DownloadIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{activeDownloads.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircleIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{completedDownloads.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircleIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{failedDownloads.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Downloads List */}
      <Card>
        <CardHeader>
          <CardTitle>Active Downloads</CardTitle>
          <CardDescription>
            Monitor and control your current downloads
          </CardDescription>
        </CardHeader>
        <CardContent>
          {downloadsQuery.isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCwIcon className="w-6 h-6 animate-spin" />
              <span className="ml-2">Loading downloads...</span>
            </div>
          ) : downloads.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <DownloadIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No active downloads</p>
            </div>
          ) : (
            <div className="space-y-4">
              {downloads.map((download) => (
                <div key={download.id} className="border rounded-lg p-4 space-y-3">
                  {/* Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusBadge(download.status)}
                      <div>
                        <h4 className="font-medium">{download.dest_path.split('/').pop()}</h4>
                        <p className="text-sm text-muted-foreground">
                          {formatBytes(download.bytes_downloaded)} / {formatBytes(download.total_bytes)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {download.status === 'downloading' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => pauseMutation.mutate(download.id)}
                          disabled={pauseMutation.isPending}
                        >
                          <PauseIcon className="w-4 h-4" />
                        </Button>
                      )}
                      {download.status === 'paused' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => resumeMutation.mutate(download.id)}
                          disabled={resumeMutation.isPending}
                        >
                          <ResumeIcon className="w-4 h-4" />
                        </Button>
                      )}
                      {download.status !== 'completed' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => cancelMutation.mutate(download.id)}
                          disabled={cancelMutation.isPending}
                        >
                          <XIcon className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>{download.progress.toFixed(1)}%</span>
                      <div className="flex items-center gap-4 text-muted-foreground">
                        {download.speed > 0 && (
                          <span className="flex items-center gap-1">
                            <ZapIcon className="w-3 h-3" />
                            {formatSpeed(download.speed)}
                          </span>
                        )}
                        {download.eta > 0 && (
                          <span className="flex items-center gap-1">
                            <TimerIcon className="w-3 h-3" />
                            {formatTime(download.eta)}
                          </span>
                        )}
                        <span>Attempt {download.attempts}</span>
                      </div>
                    </div>
                    <Progress value={download.progress} className="h-2" />
                  </div>

                  {/* Error Message */}
                  {download.error && (
                    <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                      Error: {download.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Settings Dialog */}
      <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Download Settings</DialogTitle>
            <DialogDescription>
              Configure download behavior and limits
            </DialogDescription>
          </DialogHeader>
          {settings && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="max-concurrent">Max Concurrent Downloads</Label>
                <Input
                  id="max-concurrent"
                  type="number"
                  value={settings.max_concurrent_downloads}
                  onChange={(e) => handleSettingsUpdate({ max_concurrent_downloads: parseInt(e.target.value) })}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="max-retries">Max Retries</Label>
                <Input
                  id="max-retries"
                  type="number"
                  value={settings.max_retries}
                  onChange={(e) => handleSettingsUpdate({ max_retries: parseInt(e.target.value) })}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="chunk-size">Chunk Size (bytes)</Label>
                <Input
                  id="chunk-size"
                  type="number"
                  value={settings.chunk_size}
                  onChange={(e) => handleSettingsUpdate({ chunk_size: parseInt(e.target.value) })}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="timeout">Timeout (seconds)</Label>
                <Input
                  id="timeout"
                  type="number"
                  value={settings.timeout}
                  onChange={(e) => handleSettingsUpdate({ timeout: parseInt(e.target.value) })}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="bandwidth">Bandwidth Limit (bytes/s, 0 = unlimited)</Label>
                <Input
                  id="bandwidth"
                  type="number"
                  value={settings.bandwidth_limit}
                  onChange={(e) => handleSettingsUpdate({ bandwidth_limit: parseInt(e.target.value) })}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSettingsOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => settings && updateSettingsMutation.mutate(settings)}>
              Save Settings
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}