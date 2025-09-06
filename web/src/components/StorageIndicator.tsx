import { useQuery } from '@tanstack/react-query'
import { HardDriveIcon } from 'lucide-react'
import { Progress } from './ui/progress'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'

interface StorageInfo {
  used: number
  total: number
  percentage: number
}

export function StorageIndicator() {
  const storageQuery = useQuery({
    queryKey: ['storage'],
    queryFn: async () => {
      const data = await apiClient.getStorageUsage()
      
      // Calculate total size in GB
      const totalGB = data.total_size / (1024 * 1024 * 1024)
      
      // Get available disk space (this would need a backend endpoint)
      // For now, assume 100GB total available
      const totalAvailable = 100
      const percentage = (totalGB / totalAvailable) * 100
      
      return {
        used: totalGB,
        total: totalAvailable,
        percentage: Math.min(percentage, 100), // Cap at 100%
        byType: data.by_type,
        byProject: data.by_project
      } as StorageInfo & { byType: Record<string, number>, byProject: Record<string, number> }
    },
    refetchInterval: 60_000, // Refresh every minute
  })

  if (!storageQuery.data) return null

  const { used, total, percentage } = storageQuery.data

  return (
    <div className="p-4 bg-card border border-border rounded-lg">
      <div className="flex items-center gap-3 mb-3">
        <HardDriveIcon className="h-5 w-5 text-muted-foreground" />
        <div className="flex-1">
          <h3 className="text-sm font-medium">Model Storage</h3>
          <p className="text-xs text-muted-foreground">
            {used.toFixed(1)} GB / {total} GB used
          </p>
        </div>
        <span className={cn(
          "text-sm font-medium",
          percentage > 80 ? "text-destructive" : 
          percentage > 60 ? "text-yellow-600 dark:text-yellow-500" : 
          "text-green-600 dark:text-green-500"
        )}>
          {percentage.toFixed(0)}%
        </span>
      </div>
      <Progress 
        value={percentage} 
        className={cn(
          "h-2",
          percentage > 80 && "[&>*]:bg-destructive",
          percentage > 60 && percentage <= 80 && "[&>*]:bg-yellow-600 dark:[&>*]:bg-yellow-500"
        )}
      />
    </div>
  )
}