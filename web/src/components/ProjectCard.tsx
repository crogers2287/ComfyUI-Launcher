'use client'

import { Project, Settings, ProjectRecoveryInfo, RecoveryStatus } from '@/lib/types'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import React, { useEffect } from 'react'
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from './ui/alert-dialog'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog'
import { 
    Loader2Icon, 
    PlayIcon, 
    StopCircleIcon, 
    TrashIcon, 
    ExternalLinkIcon,
    RefreshCw,
    Pause,
    AlertTriangle
} from 'lucide-react'
import { DialogDescription } from '@radix-ui/react-dialog'
import { cn } from '@/lib/utils'

type ProjectCardProps = {
    item: Project
    settings: Settings
    recoveryInfo?: ProjectRecoveryInfo
}

const getProjectURL = (port: number, settings: Settings) => {
    // get the window location
    const { location } = window

    // Support proxying for Runpod
    // check if the current origin matches this pattern: https://<pod id>-<port number>.proxy.runpod.net
    const match = location.origin.match(
        /^https:\/\/([a-zA-Z0-9]+)-([0-9]+)\.proxy\.runpod\.net$/
    )
    if (match) {
        // if it does, replace the port number with the new port number
        return `https://${match[1]}-${port}.proxy.runpod.net`
    }

    if (settings.PROXY_MODE) {
        return `/comfy/${port}/`; // proxy mode
    }

    // otherwise, replace the port in the current origin with the new port number
    return location.origin.replace(/:[0-9]+$/, `:${port}`)
}

function ProjectCard({ item, settings, recoveryInfo }: ProjectCardProps) {
    const queryClient = useQueryClient()

    const [deleteProjectDialogOpen, setDeleteProjectDialogOpen] =
        React.useState(false)

    const [projectOperation, setProjectOperation] = React.useState<
        'launch' | 'stop' | 'delete'
    >()
    const [projectStatusDialogOpen, setProjectStatusDialogOpen] =
        React.useState(false)

    const launchProjectMutation = useMutation({
        mutationFn: async () => {
            const response = await fetch(`/api/projects/${item.id}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            const data = await response.json()
            return data
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['projects'] })
        },
    })

    const stopProjectMutation = useMutation({
        mutationFn: async () => {
            const response = await fetch(`/api/projects/${item.id}/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            const data = await response.json()
            return data
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['projects'] })
        },
    })

    const deleteProjectMutation = useMutation({
        mutationFn: async () => {
            const response = await fetch(`/api/projects/${item.id}/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            const data = await response.json()
            return data
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['projects'] })
        },
    })

    useEffect(() => {
        if (launchProjectMutation.isPending) {
            setProjectOperation('launch')
        } else if (deleteProjectMutation.isPending) {
            setProjectOperation('delete')
        } else if (stopProjectMutation.isPending) {
            setProjectOperation('stop')
        } else {
            setProjectOperation(undefined)
        }
        setProjectStatusDialogOpen(
            launchProjectMutation.isPending ||
                stopProjectMutation.isPending ||
                deleteProjectMutation.isPending
        )
    }, [
        launchProjectMutation.isPending,
        stopProjectMutation.isPending,
        deleteProjectMutation.isPending,
    ])

    // Recovery info helpers
    const activeRecoveryOperations = recoveryInfo?.active_operations?.filter(
        op => op.state === 'recovering' || op.state === 'in_progress'
    ) || []
    
    const hasActiveRecovery = activeRecoveryOperations.length > 0
    const totalRecoveryAttempts = recoveryInfo?.total_attempts || 0

    const getRecoveryStatusIcon = (operation: RecoveryStatus) => {
        switch (operation.state) {
            case 'recovering':
                return <RefreshCw className="h-3 w-3 animate-spin" />
            case 'in_progress':
                return <Loader2Icon className="h-3 w-3 animate-spin" />
            case 'pending':
                return <Pause className="h-3 w-3" />
            case 'failed':
            case 'exhausted':
                return <AlertTriangle className="h-3 w-3" />
            default:
                return null
        }
    }

    const pauseRecovery = async (operationId: string) => {
        // TODO: Implement pause recovery API call
        console.log('Pausing recovery:', operationId)
    }

    return (
        <>
            <Dialog
                onOpenChange={(open) => setProjectStatusDialogOpen(open)}
                open={!!projectOperation && projectStatusDialogOpen}
            >
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        {projectOperation === 'launch' && (
                            <DialogTitle>Launching project...</DialogTitle>
                        )}
                        {projectOperation === 'stop' && (
                            <DialogTitle>Stopping project...</DialogTitle>
                        )}
                        {projectOperation === 'delete' && (
                            <DialogTitle>Deleting project...</DialogTitle>
                        )}
                        <DialogDescription className="mt-5 text-sm text-neutral-700 font-medium">
                            This could take a few moments.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="flex justify-center items-center">
                        <Loader2Icon className="animate-spin h-10 w-10 text-gray-700" />
                    </div>
                </DialogContent>
            </Dialog>
            <AlertDialog
                open={deleteProjectDialogOpen}
                onOpenChange={(open) => setDeleteProjectDialogOpen(open)}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. This will permanently
                            delete your project&apos;s data. Your models will
                            NOT be deleted.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => {
                                e.preventDefault()
                                setDeleteProjectDialogOpen(false)
                                deleteProjectMutation.mutate()
                            }}
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
            <div
                className={cn(
                    'group relative rounded-lg p-6 border transition-all duration-200',
                    'bg-card hover:shadow-lg hover:scale-[1.02]',
                    'border-border dark:hover:border-primary/20',
                    item.state.state === 'running' && 'ring-2 ring-primary/20'
                )}
            >
                {/* Status Indicators */}
                <div className="absolute top-3 right-3 flex items-center gap-2">
                    {/* Recovery Status */}
                    {hasActiveRecovery && (
                        <Badge variant="outline" className="text-xs flex items-center gap-1">
                            <RefreshCw className="h-3 w-3 animate-spin" />
                            Recovery ({activeRecoveryOperations.length})
                        </Badge>
                    )}
                    {totalRecoveryAttempts > 0 && !hasActiveRecovery && (
                        <Badge variant="secondary" className="text-xs">
                            {totalRecoveryAttempts} attempts
                        </Badge>
                    )}
                    
                    {/* Project Status */}
                    <div
                        className={cn(
                            'h-3 w-3 rounded-full',
                            item.state.state === 'ready' && 'bg-gray-400',
                            item.state.state === 'running' && 'bg-green-500 animate-pulse',
                            item.state.state !== 'ready' && item.state.state !== 'running' && 'bg-yellow-500',
                            hasActiveRecovery && 'ring-2 ring-blue-500/50'
                        )}
                        title={hasActiveRecovery ? `${item.state.state} (recovering)` : item.state.state}
                    />
                </div>

                <div className="flex flex-col space-y-4">
                    <div className="flex flex-col">
                        <h1 className="text-lg font-semibold text-foreground">
                            {item.state.name}
                        </h1>
                        <p className="mt-1 font-medium text-xs text-muted-foreground font-mono">
                            ID: {item.id}
                        </p>
                    </div>
                    
                    {item.state.status_message && item.state.status_message.length > 0 && (
                        <div className="flex flex-row items-center space-x-2">
                            {item.state.state !== "ready" && 
                                <Loader2Icon className="animate-spin h-4 w-4 text-muted-foreground" />
                            }
                            <p className='text-sm italic text-muted-foreground'>
                                {item.state.status_message}
                            </p>
                        </div>
                    )}

                    {/* Recovery Operations */}
                    {activeRecoveryOperations.length > 0 && (
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-foreground flex items-center gap-2">
                                <RefreshCw className="h-4 w-4 animate-spin" />
                                Active Recovery Operations
                            </div>
                            {activeRecoveryOperations.slice(0, 2).map((operation) => (
                                <div key={operation.operation_id} className="bg-muted/50 rounded p-2 text-sm">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2 min-w-0 flex-1">
                                            {getRecoveryStatusIcon(operation)}
                                            <span className="truncate">{operation.operation_name}</span>
                                            <Badge variant="outline" className="text-xs">
                                                {operation.attempt}/{operation.max_attempts}
                                            </Badge>
                                        </div>
                                        <div className="flex gap-1 ml-2">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-6 w-6 p-0"
                                                onClick={() => pauseRecovery(operation.operation_id)}
                                                title="Pause recovery"
                                            >
                                                <Pause className="h-3 w-3" />
                                            </Button>
                                        </div>
                                    </div>
                                    {operation.error && (
                                        <div className="text-xs text-destructive mt-1 truncate">
                                            {operation.error}
                                        </div>
                                    )}
                                </div>
                            ))}
                            {activeRecoveryOperations.length > 2 && (
                                <div className="text-xs text-muted-foreground text-center">
                                    ... and {activeRecoveryOperations.length - 2} more operations
                                </div>
                            )}
                        </div>
                    )}
                    
                    {/* Action buttons with icons */}
                    <div className="flex flex-row space-x-2 pt-2">
                        {item.state.state === 'ready' && (
                            <Button
                                onClick={(e) => {
                                    e.preventDefault()
                                    launchProjectMutation.mutate()
                                }}
                                variant="default"
                                size="sm"
                                className="flex items-center gap-2"
                            >
                                <PlayIcon className="h-4 w-4" />
                                Launch
                            </Button>
                        )}
                        {item.state.state === 'running' && !!item.state.port && (
                            <Button variant="default" size="sm" asChild>
                                <a
                                    href={getProjectURL(item.state.port, settings)}
                                    target="_blank"
                                    className="flex items-center gap-2"
                                >
                                    <ExternalLinkIcon className="h-4 w-4" />
                                    Open
                                </a>
                            </Button>
                        )}
                        {item.state.state === 'running' && (
                            <Button
                                onClick={(e) => {
                                    e.preventDefault()
                                    stopProjectMutation.mutate()
                                }}
                                variant="secondary"
                                size="sm"
                                className="flex items-center gap-2"
                            >
                                <StopCircleIcon className="h-4 w-4" />
                                Stop
                            </Button>
                        )}
                        <Button
                            onClick={(e) => {
                                e.preventDefault()
                                setDeleteProjectDialogOpen(true)
                            }}
                            variant="ghost"
                            size="sm"
                            className="flex items-center gap-2 hover:text-destructive"
                        >
                            <TrashIcon className="h-4 w-4" />
                            Delete
                        </Button>
                    </div>
                </div>
            </div>
        </>
    )
}

export default ProjectCard
