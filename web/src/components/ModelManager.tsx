import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { ScrollArea } from './ui/scroll-area'
import { Badge } from './ui/badge'
import { 
  DownloadIcon, 
  TrashIcon, 
  SearchIcon, 
  FileIcon,
  Loader2Icon 
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'
import { toast } from 'sonner'
import { subscribeToProgress, ProgressEvent } from '@/lib/socket'
import { Progress } from './ui/progress'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'

interface ModelManagerProps {
  className?: string
}

export function ModelManager({ className }: ModelManagerProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [downloadUrl, setDownloadUrl] = useState('')
  const [downloadName, setDownloadName] = useState('')
  const [downloadType, setDownloadType] = useState('checkpoint')
  const [isDownloadDialogOpen, setIsDownloadDialogOpen] = useState(false)
  const [downloadProgress, setDownloadProgress] = useState<ProgressEvent | null>(null)
  const queryClient = useQueryClient()

  const modelsQuery = useQuery({
    queryKey: ['models', selectedType],
    queryFn: async () => {
      return apiClient.getModels(selectedType === 'all' ? undefined : selectedType)
    },
  })

  const deleteModelMutation = useMutation({
    mutationFn: async (modelPath: string) => {
      await apiClient.deleteModel(modelPath)
    },
    onSuccess: () => {
      toast.success('Model deleted successfully')
      queryClient.invalidateQueries({ queryKey: ['models'] })
      queryClient.invalidateQueries({ queryKey: ['storage'] })
    },
    onError: (error) => {
      toast.error(`Failed to delete model: ${error.message}`)
    },
  })

  const downloadModelMutation = useMutation({
    mutationFn: async (data: { url: string; name: string; type: string }) => {
      const result = await apiClient.downloadModel(data)
      
      // Subscribe to download progress
      if (result.task_id) {
        const unsubscribe = subscribeToProgress(result.task_id, (progress) => {
          setDownloadProgress(progress)
          
          if (progress.status === 'completed') {
            toast.success('Model downloaded successfully!')
            setIsDownloadDialogOpen(false)
            setDownloadProgress(null)
            queryClient.invalidateQueries({ queryKey: ['models'] })
            queryClient.invalidateQueries({ queryKey: ['storage'] })
          } else if (progress.status === 'failed') {
            toast.error(`Download failed: ${progress.message}`)
            setDownloadProgress(null)
          }
        })
        
        // Store unsubscribe function for cleanup
        return unsubscribe
      }
    },
    onError: (error) => {
      toast.error(`Failed to start download: ${error.message}`)
    },
  })

  const filteredModels = modelsQuery.data?.filter(model => 
    model.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  const modelTypes = ['all', 'checkpoint', 'lora', 'vae', 'controlnet', 'embedding']

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>Model Manager</CardTitle>
        <CardDescription>
          Manage your ComfyUI models
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Search and Filters */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search models..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button
              onClick={() => setIsDownloadDialogOpen(true)}
              size="sm"
            >
              <DownloadIcon className="h-4 w-4 mr-2" />
              Download Model
            </Button>
          </div>

          {/* Model Type Tabs */}
          <div className="flex gap-2 border-b overflow-x-auto">
            {modelTypes.map(type => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className={cn(
                  "px-3 py-2 text-sm font-medium capitalize transition-colors whitespace-nowrap",
                  "border-b-2 -mb-[2px]",
                  selectedType === type 
                    ? "border-primary text-primary" 
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Models List */}
          <ScrollArea className="h-[400px]">
            {modelsQuery.isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2Icon className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : filteredModels.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No models found
              </div>
            ) : (
              <div className="space-y-2">
                {filteredModels.map((model) => (
                  <div
                    key={model.path}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-md hover:bg-muted/70 transition-colors"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <FileIcon className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{model.name}</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="secondary" className="text-xs">
                            {model.type}
                          </Badge>
                          <span>{formatFileSize(model.size)}</span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deleteModelMutation.mutate(model.path)}
                      disabled={deleteModelMutation.isPending}
                      className="shrink-0"
                    >
                      <TrashIcon className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      </CardContent>

      {/* Download Model Dialog */}
      <Dialog open={isDownloadDialogOpen} onOpenChange={setIsDownloadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Download Model</DialogTitle>
            <DialogDescription>
              Enter the URL of the model you want to download
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="url">Model URL</Label>
              <Input
                id="url"
                placeholder="https://huggingface.co/..."
                value={downloadUrl}
                onChange={(e) => setDownloadUrl(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="name">Model Name</Label>
              <Input
                id="name"
                placeholder="my-model.safetensors"
                value={downloadName}
                onChange={(e) => setDownloadName(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="type">Model Type</Label>
              <select
                id="type"
                value={downloadType}
                onChange={(e) => setDownloadType(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="checkpoint">Checkpoint</option>
                <option value="lora">LoRA</option>
                <option value="vae">VAE</option>
                <option value="controlnet">ControlNet</option>
                <option value="embedding">Embedding</option>
              </select>
            </div>

            {downloadProgress && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  {downloadProgress.message}
                </p>
                <Progress 
                  value={
                    downloadProgress.progress || 
                    (downloadProgress.current && downloadProgress.total
                      ? (downloadProgress.current / downloadProgress.total) * 100
                      : 0)
                  } 
                />
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsDownloadDialogOpen(false)}
              disabled={downloadModelMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (downloadUrl && downloadName && downloadType) {
                  downloadModelMutation.mutate({
                    url: downloadUrl,
                    name: downloadName,
                    type: downloadType,
                  })
                }
              }}
              disabled={!downloadUrl || !downloadName || downloadModelMutation.isPending}
            >
              {downloadModelMutation.isPending ? (
                <>
                  <Loader2Icon className="h-4 w-4 mr-2 animate-spin" />
                  Downloading...
                </>
              ) : (
                'Download'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}