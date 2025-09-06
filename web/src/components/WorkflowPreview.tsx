import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { ScrollArea } from './ui/scroll-area'
import { InfoIcon, CpuIcon, PackageIcon, AlertCircleIcon, CheckCircleIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'
import { WorkflowValidation } from '@/lib/api'

interface WorkflowData {
  nodes: any[]
  links: any[]
  version?: number
  groups?: any[]
  config?: any
  extra?: any
}

interface WorkflowPreviewProps {
  workflowData: WorkflowData | null
  className?: string
}

export function WorkflowPreview({ workflowData, className }: WorkflowPreviewProps) {
  const [selectedTab, setSelectedTab] = useState<'overview' | 'nodes' | 'validation' | 'raw'>('overview')
  const [validation, setValidation] = useState<WorkflowValidation | null>(null)
  const [isValidating, setIsValidating] = useState(false)

  useEffect(() => {
    if (workflowData) {
      validateWorkflow()
    }
  }, [workflowData])

  const validateWorkflow = async () => {
    if (!workflowData) return
    
    setIsValidating(true)
    try {
      const result = await apiClient.validateWorkflow(workflowData)
      setValidation(result)
    } catch (error) {
      console.error('Failed to validate workflow:', error)
      setValidation({
        valid: false,
        errors: ['Failed to validate workflow'],
      })
    } finally {
      setIsValidating(false)
    }
  }

  if (!workflowData) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="flex items-center justify-center h-64 text-muted-foreground">
          <p>No workflow data to preview</p>
        </CardContent>
      </Card>
    )
  }

  // Extract node types
  const nodeTypes = [...new Set(workflowData.nodes.map(node => node.type))]
  const nodeCount = workflowData.nodes.length
  const linkCount = workflowData.links?.length || 0

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="text-lg">Workflow Preview</CardTitle>
        <CardDescription>
          Analyze workflow before importing
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Tab Navigation */}
          <div className="flex gap-2 border-b">
            <button
              onClick={() => setSelectedTab('overview')}
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors",
                "border-b-2 -mb-[2px]",
                selectedTab === 'overview' 
                  ? "border-primary text-primary" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              Overview
            </button>
            <button
              onClick={() => setSelectedTab('nodes')}
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors",
                "border-b-2 -mb-[2px]",
                selectedTab === 'nodes' 
                  ? "border-primary text-primary" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              Nodes ({nodeCount})
            </button>
            <button
              onClick={() => setSelectedTab('validation')}
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors",
                "border-b-2 -mb-[2px] flex items-center gap-1",
                selectedTab === 'validation' 
                  ? "border-primary text-primary" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              Validation
              {validation && (
                validation.valid ? (
                  <CheckCircleIcon className="h-3 w-3 text-green-600" />
                ) : (
                  <AlertCircleIcon className="h-3 w-3 text-destructive" />
                )
              )}
            </button>
            <button
              onClick={() => setSelectedTab('raw')}
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors",
                "border-b-2 -mb-[2px]",
                selectedTab === 'raw' 
                  ? "border-primary text-primary" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              Raw JSON
            </button>
          </div>

          {/* Tab Content */}
          <div className="min-h-[200px]">
            {selectedTab === 'overview' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-primary/10">
                      <CpuIcon className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{nodeCount} Nodes</p>
                      <p className="text-xs text-muted-foreground">Processing units</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-primary/10">
                      <PackageIcon className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{linkCount} Links</p>
                      <p className="text-xs text-muted-foreground">Connections</p>
                    </div>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium mb-2">Node Types Used:</p>
                  <div className="flex flex-wrap gap-2">
                    {nodeTypes.slice(0, 10).map(type => (
                      <Badge key={type} variant="secondary" className="text-xs">
                        {type}
                      </Badge>
                    ))}
                    {nodeTypes.length > 10 && (
                      <Badge variant="outline" className="text-xs">
                        +{nodeTypes.length - 10} more
                      </Badge>
                    )}
                  </div>
                </div>

                {workflowData.extra && (
                  <div className="p-3 bg-muted/50 rounded-md">
                    <div className="flex items-center gap-2 mb-1">
                      <InfoIcon className="h-4 w-4 text-muted-foreground" />
                      <p className="text-sm font-medium">Additional Info</p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Workflow version: {workflowData.version || 'Unknown'}
                    </p>
                  </div>
                )}
              </div>
            )}

            {selectedTab === 'nodes' && (
              <ScrollArea className="h-[300px]">
                <div className="space-y-2">
                  {workflowData.nodes.map((node, index) => (
                    <div key={index} className="p-3 bg-muted/50 rounded-md">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium">{node.type}</p>
                        <Badge variant="outline" className="text-xs">
                          ID: {node.id}
                        </Badge>
                      </div>
                      {node.widgets_values && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {node.widgets_values.length} parameters
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}

            {selectedTab === 'validation' && (
              <div className="space-y-4">
                {isValidating ? (
                  <div className="flex items-center justify-center py-8">
                    <p className="text-sm text-muted-foreground">Validating workflow...</p>
                  </div>
                ) : validation ? (
                  <>
                    <div className={cn(
                      "flex items-center gap-2 p-3 rounded-md",
                      validation.valid ? "bg-green-50 dark:bg-green-950" : "bg-red-50 dark:bg-red-950"
                    )}>
                      {validation.valid ? (
                        <CheckCircleIcon className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircleIcon className="h-4 w-4 text-destructive" />
                      )}
                      <p className={cn(
                        "text-sm font-medium",
                        validation.valid ? "text-green-800 dark:text-green-200" : "text-red-800 dark:text-red-200"
                      )}>
                        {validation.valid ? "Workflow is valid" : "Workflow has issues"}
                      </p>
                    </div>

                    {validation.errors && validation.errors.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Errors:</p>
                        <ul className="space-y-1">
                          {validation.errors.map((error, i) => (
                            <li key={i} className="text-sm text-destructive flex items-start gap-2">
                              <span className="mt-0.5">•</span>
                              <span>{error}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {validation.warnings && validation.warnings.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Warnings:</p>
                        <ul className="space-y-1">
                          {validation.warnings.map((warning, i) => (
                            <li key={i} className="text-sm text-yellow-600 dark:text-yellow-500 flex items-start gap-2">
                              <span className="mt-0.5">•</span>
                              <span>{warning}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {validation.missing_models && validation.missing_models.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Missing Models:</p>
                        <div className="flex flex-wrap gap-2">
                          {validation.missing_models.map((model, i) => (
                            <Badge key={i} variant="destructive" className="text-xs">
                              {model}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {validation.required_nodes && validation.required_nodes.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Required Nodes:</p>
                        <div className="flex flex-wrap gap-2">
                          {validation.required_nodes.map((node, i) => (
                            <Badge key={i} variant="secondary" className="text-xs">
                              {node}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No validation data available
                  </p>
                )}
              </div>
            )}

            {selectedTab === 'raw' && (
              <ScrollArea className="h-[300px]">
                <pre className="text-xs font-mono bg-muted/50 p-3 rounded-md">
                  {JSON.stringify(workflowData, null, 2)}
                </pre>
              </ScrollArea>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}