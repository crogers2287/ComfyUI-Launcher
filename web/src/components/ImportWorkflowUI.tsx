'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from './ui/button'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from './ui/dialog'
import { Input } from './ui/input'
import { Loader2Icon, FileJsonIcon, UploadCloudIcon, Sparkles, FileArchiveIcon, Link2Icon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import {
    MissingModel,
    ResolvedMissingModelFile,
    Settings,
    Source,
} from '@/lib/types'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import MissingModelItem from './MissingModelItem'
import { Checkbox } from './ui/checkbox'
import { Progress } from './ui/progress'
import { cn } from '@/lib/utils'
import { WorkflowPreview } from './WorkflowPreview'
import { subscribeToProgress, ProgressEvent } from '@/lib/socket'
import { apiClient } from '@/lib/api'

const baseStyle = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '40px',
    borderWidth: 2,
    borderRadius: 12,
    borderStyle: 'dashed',
    outline: 'none',
    transition: 'all .24s ease-in-out',
    cursor: 'pointer',
}

const focusedStyle = {
    borderColor: 'hsl(var(--primary))',
    backgroundColor: 'hsl(var(--primary) / 0.05)',
}

const acceptStyle = {
    borderColor: '#00e676',
    backgroundColor: '#00e67610',
}

const rejectStyle = {
    borderColor: 'hsl(var(--destructive))',
    backgroundColor: 'hsl(var(--destructive) / 0.05)',
}

function ImportWorkflowUI() {
    const [importJson, setImportJson] = React.useState<string>()
    const [parsedWorkflow, setParsedWorkflow] = React.useState<any>(null)

    const queryClient = useQueryClient()
    const navigate = useNavigate()


    const getSettingsQuery = useQuery({
        queryKey: ['settings'],
        queryFn: async () => {
            const response = await fetch(`/api/settings`)
            const data = await response.json()
            return data as Settings
        },
    })

    const [projectName, setProjectName] = React.useState('')
    const [importProjectDialogOpen, setImportProjectDialogOpen] =
        React.useState(false)
    const [projectStatusDialogOpen, setProjectStatusDialogOpen] =
        React.useState(false)
    const [importProgress, setImportProgress] = useState<ProgressEvent | null>(null)
    // const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
    const [useFixedPort, setUseFixedPort] = React.useState(false)
    const [fixedPort, setFixedPort] = React.useState(4001)

    const [missingModels, setMissingModels] = React.useState<MissingModel[]>([])
    const [resolvedMissingModels, setResolvedMissingModels] = React.useState<
        ResolvedMissingModelFile[]
    >([])
    const [resolvedAllModels, setResolvedAllModels] = useState(false)
    const [
        confirmOnlyPartiallyResolvingOpen,
        setConfirmOnlyPartiallyResolvingOpen,
    ] = useState(false)
    const [isAutoResolving, setIsAutoResolving] = useState(false)
    const [autoResolveProgress, setAutoResolveProgress] = useState<string | null>(null)
    const [workflowUrl, setWorkflowUrl] = useState('')
    const [isLoadingFromUrl, setIsLoadingFromUrl] = useState(false)
    
    // Move these state declarations before the mutation hooks to avoid hooks order violations
    const [uploadedFile, setUploadedFile] = React.useState<File | null>(null)
    const [isZipFile, setIsZipFile] = React.useState(false)

    const importProjectMutation = useMutation({
        mutationFn: async ({
            import_json,
            name,
            partiallyResolved,
            useFixedPort,
            port,
        }: {
            import_json: string
            name: string
            partiallyResolved?: boolean
            useFixedPort: boolean
            port: number
        }) => {
            // Check if this is a ZIP file import
            if (isZipFile && uploadedFile) {
                // Handle ZIP file upload
                const formData = new FormData()
                formData.append('file', uploadedFile)
                formData.append('name', name)
                formData.append('resolved_missing_models', JSON.stringify(resolvedMissingModels))
                formData.append('skipping_model_validation', partiallyResolved ? 'true' : 'false')
                if (useFixedPort) {
                    formData.append('port', port.toString())
                }
                
                const response = await fetch(`/api/import_project_zip`, {
                    method: 'POST',
                    body: formData,
                })
                const data = await response.json()
                
                if (!data.success && data.missing_models) {
                    const formattedMissingModels: MissingModel[] = Array.isArray(data.missing_models)
                        ? data.missing_models.map((model: any) => ({
                            filename: model.filename || '',
                            node_type: model.node_type || 'unknown',
                            dest_relative_path: model.dest_relative_path || '',
                            suggestions: []
                        }))
                        : [data.missing_models].map((model: any) => ({
                            filename: model.filename || '',
                            node_type: model.node_type || 'unknown',
                            dest_relative_path: model.dest_relative_path || '',
                            suggestions: []
                        }));
                    setMissingModels(formattedMissingModels)
                } else if (!data.success && !!data.error) {
                    console.error('error importing workflow:', data.error)
                    toast.error(data.error)
                } else {
                    navigate('/')
                    if (data.assets_found > 0) {
                        toast.success(`Imported workflow with ${data.assets_found} assets`)
                    }
                }
                return data
            } else {
                // Handle regular JSON import
                const final_import_json = JSON.parse(import_json)
                const uniqueFilenames = new Set()
                const uniqueResolvedMissingModels = resolvedMissingModels.filter(
                    (model) => {
                        if (uniqueFilenames.has(model.filename)) {
                            return false
                        }
                        uniqueFilenames.add(model.filename)
                        return true
                    }
                )

                const partiallyResolvedBool = partiallyResolved ? true : false
                const response = await fetch(`/api/import_project`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        import_json: final_import_json,
                        resolved_missing_models: uniqueResolvedMissingModels,
                        skipping_model_validation: partiallyResolvedBool,
                        name,
                        useFixedPort,
                        port: useFixedPort ? port : undefined,
                    }),
                })
                const data = await response.json()
                if (!data.success && data.missing_models) {
                    const formattedMissingModels: MissingModel[] = Array.isArray(data.missing_models)
                        ? data.missing_models.map((model: any) => ({
                            filename: model.filename || '',
                            node_type: model.node_type || 'unknown',
                            dest_relative_path: model.dest_relative_path || '',
                            suggestions: []
                        }))
                        : [data.missing_models].map((model: any) => ({
                            filename: model.filename || '',
                            node_type: model.node_type || 'unknown',
                            dest_relative_path: model.dest_relative_path || '',
                            suggestions: []
                        }));
                    setMissingModels(formattedMissingModels)
                } else if (!data.success && !!data.error) {
                    console.error('error importing workflow:', data.error)
                    toast.error(data.error)
                } else if (data.task_id && data.project_id) {
                    // Store task ID for progress tracking
                    // setCurrentTaskId(data.task_id)
                    
                    // Subscribe to progress updates
                    const unsubscribe = subscribeToProgress(
                        data.project_id,
                        (progress) => {
                            setImportProgress(progress)
                            
                            if (progress.status === 'completed') {
                                toast.success('Workflow imported successfully!')
                                setTimeout(() => navigate('/'), 1000)
                            } else if (progress.status === 'failed') {
                                toast.error(`Import failed: ${progress.message}`)
                                setProjectStatusDialogOpen(false)
                            }
                        }
                    )
                    
                    // Clean up subscription when component unmounts
                    return () => unsubscribe()
                } else {
                    navigate('/')
                }
                return data
            }
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ['projects'] })
        },
    })

    const resolveMissingModelMutationWithSuggestion = useMutation({
        mutationFn: async ({
            filename,
            node_type,
            dest_relative_path,
            source,
        }: {
            filename: string
            node_type: string
            dest_relative_path: string
            source: Source
        }) => {
            if (!filename || !node_type || !source) {
                toast.error(
                    'something went wrong when resolving your model. please try again.'
                )
                return
            }

            try {
                // const newItem = { filename: filename, node_type: node_type, source: source };
                // const newSet = new Set(resolvedMissingModels);
                // newSet.add(newItem);
                // setResolvedMissingModels(newSet);
                setResolvedMissingModels([
                    ...resolvedMissingModels,
                    {
                        filename: filename,
                        node_type: node_type,
                        dest_relative_path: dest_relative_path,
                        source: source,
                    },
                ])
            } catch (error: unknown) {
                toast.error(
                    'something went wrong when resolving your model. please try again.'
                )
                return
            }

            toast.success('successfully resolved')

            return
        },
    })

    const unResolveMissingModelMutationWithSuggestion = useMutation({
        mutationFn: async ({ filename }: { filename: string }) => {
            if (!filename) {
                toast.error(
                    'something went wrong when attempting to edit your model. please try again.'
                )
                return
            }

            try {
                // const itemToRemove = { filename: "example", node_type: "example" };
                // const updatedSet = new Set([...resolvedMissingModels].filter(item => item !== itemToRemove));
                // setResolvedMissingModels(updatedSet);
                setResolvedMissingModels(
                    resolvedMissingModels.filter(
                        (missingModel) => missingModel.filename !== filename
                    )
                )
            } catch (error: unknown) {
                toast.error(
                    'something went wrong when attempting to edit your model. please try again.'
                )
                return
            }

            // toast.success("successfully resolved")

            return
        },
    })

    useEffect(() => {
        if (
            missingModels &&
            missingModels.length > 0 &&
            resolvedMissingModels &&
            resolvedMissingModels.length > 0 &&
            missingModels.length === resolvedMissingModels.length
        ) {
            console.log('RESOLVED all missing models')
            setResolvedAllModels(true)
        } else {
            console.log('HAVE NOT RESOLVED all missing models')
            setResolvedAllModels(false)
        }
    }, [missingModels, resolvedMissingModels])

    useEffect(() => {
        setProjectStatusDialogOpen(importProjectMutation.isPending)
        if (importProjectMutation.isPending) {
            setConfirmOnlyPartiallyResolvingOpen(false)
        }
    }, [importProjectMutation.isPending])

    const onDrop = useCallback(
        (acceptedFiles: File[]) => {
            if (acceptedFiles.length === 0) {
                setImportJson(undefined)
                setUploadedFile(null)
                setIsZipFile(false)
                setParsedWorkflow(null)
                return
            }
            
            const file = acceptedFiles[0]
            setUploadedFile(file)
            
            // Check if it's a ZIP file
            if (file.name.toLowerCase().endsWith('.zip')) {
                setIsZipFile(true)
                // For ZIP files, we'll handle them differently during import
                // We don't need to read the content here
                setParsedWorkflow(null)
                setImportJson(JSON.stringify({ isZipFile: true, fileName: file.name }))
                toast.success('ZIP file loaded. Workflow will be extracted during import.')
            } else {
                // Handle JSON files as before
                setIsZipFile(false)
                const reader = new FileReader()
                reader.onabort = () => {
                    console.log('file reading was aborted')
                    toast.error('File reading was aborted')
                    setImportJson(undefined)
                    setParsedWorkflow(null)
                }
                reader.onerror = () => {
                    console.log('file reading has failed')
                    toast.error('Failed to read file')
                    setImportJson(undefined)
                    setParsedWorkflow(null)
                }
                reader.onload = () => {
                    // Do whatever you want with the file contents
                    const binaryStr = reader.result // string | ArrayBuffer | null
                    if (!binaryStr) {
                        setImportJson(undefined)
                        toast.error('File is empty or could not be read')
                        return
                    }
                    if (typeof binaryStr === 'string') {
                        setImportJson(binaryStr)
                        try {
                            const parsed = JSON.parse(binaryStr)
                            // Validate it's a ComfyUI workflow
                            if (!parsed || typeof parsed !== 'object') {
                                throw new Error('Invalid JSON structure')
                            }
                            const hasNodes = parsed.nodes || parsed['1'] // Support both formats
                            if (!hasNodes) {
                                throw new Error('Not a valid ComfyUI workflow - missing nodes')
                            }
                            setParsedWorkflow(parsed)
                            toast.success('Workflow loaded successfully!')
                            
                            // Validate workflow for missing models
                            validateWorkflowForMissingModels(parsed)
                        } catch (e) {
                            console.error('Failed to parse workflow JSON:', e)
                            setParsedWorkflow(null)
                            const errorMessage = e instanceof Error ? e.message : 'Invalid JSON format'
                            toast.error(`Failed to parse workflow: ${errorMessage}`)
                        }
                    } else {
                        const bytes = new Uint8Array(binaryStr)
                        const arr = []
                        for (var i = 0; i < bytes.length; i++) {
                            arr.push(String.fromCharCode(bytes[i]))
                        }
                        const bstr = arr.join('')
                        setImportJson(bstr)
                        try {
                            const parsed = JSON.parse(bstr)
                            // Validate it's a ComfyUI workflow
                            if (!parsed || typeof parsed !== 'object') {
                                throw new Error('Invalid JSON structure')
                            }
                            const hasNodes = parsed.nodes || parsed['1'] // Support both formats
                            if (!hasNodes) {
                                throw new Error('Not a valid ComfyUI workflow - missing nodes')
                            }
                            setParsedWorkflow(parsed)
                            toast.success('Workflow loaded successfully!')
                            
                            // Validate workflow for missing models
                            validateWorkflowForMissingModels(parsed)
                        } catch (e) {
                            console.error('Failed to parse workflow JSON:', e)
                            setParsedWorkflow(null)
                            const errorMessage = e instanceof Error ? e.message : 'Invalid JSON format'
                            toast.error(`Failed to parse workflow: ${errorMessage}`)
                        }
                    }
                }
                reader.readAsArrayBuffer(file)
            }
        },
        [setImportJson]
    )

    const handleImportFromUrl = async () => {
        if (!workflowUrl || workflowUrl.trim() === '') {
            toast.error('Please enter a workflow URL')
            return
        }

        // Validate URL format
        try {
            new URL(workflowUrl)
        } catch (e) {
            toast.error('Please enter a valid URL')
            return
        }

        setIsLoadingFromUrl(true)
        try {
            // Fetch the workflow JSON from the URL via backend to avoid CORS
            const response = await fetch('/api/fetch_workflow_from_url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: workflowUrl }),
            })
            
            if (!response.ok) {
                let errorMessage = `Failed to fetch workflow: ${response.statusText}`
                try {
                    const errorData = await response.json()
                    errorMessage = errorData.error || errorMessage
                } catch (e) {
                    // If response is not JSON, use default error message
                }
                throw new Error(errorMessage)
            }
            
            const data = await response.json()
            
            // Validate the response
            if (!data.success || !data.workflow) {
                throw new Error('Invalid workflow data received from server')
            }
            
            // Validate workflow structure
            const workflowJson = data.workflow
            if (!workflowJson || typeof workflowJson !== 'object') {
                throw new Error('Invalid workflow JSON structure')
            }
            
            // Check if it's a valid ComfyUI workflow
            const hasNodes = workflowJson.nodes || workflowJson['1'] // Support both formats
            if (!hasNodes) {
                throw new Error('Not a valid ComfyUI workflow - missing nodes')
            }
            
            const workflowText = JSON.stringify(workflowJson)
            
            setImportJson(workflowText)
            setParsedWorkflow(workflowJson)
            
            // Automatically trigger auto-resolve for all models
            toast.info('Workflow loaded. Auto-resolving models...')
            
            // First check for missing models using the auto-resolve endpoint
            try {
                const result = await apiClient.autoResolveModels(workflowJson)
                
                if (result && result.error === 'MISSING_MODELS' && result.ai_search_enabled && result.missing_models) {
                    const detectedMissingModels = result.missing_models.map(m => {
                        // Convert AI suggestions to the expected format
                        const suggestions = (m.ai_suggestions || []).map(s => ({
                            filename: s.filename,
                            source: (s.source === 'civitai' ? 'civitai' : 'hf') as 'civitai' | 'hf',
                            filepath: '',
                            hf_file_id: s.hf_file_id || null,
                            civitai_file_id: s.civitai_file_id || null,
                            url: s.url || s.download_url || '',
                            node_type: s.node_type,
                            sha256_checksum: s.sha256_checksum || null,
                        }))
                        
                        return {
                            filename: m.filename,
                            node_type: m.node_type,
                            dest_relative_path: m.dest_relative_path,
                            suggestions
                        } as MissingModel
                    })
                    setMissingModels(detectedMissingModels)
                    
                    let totalResolved = 0
                    const newResolvedModels: ResolvedMissingModelFile[] = []
                    
                    // Update missing models with AI suggestions and auto-resolve
                    const updatedMissingModels = detectedMissingModels.map((model: MissingModel) => {
                        const aiResult = result.missing_models?.find(
                            m => m.filename === model.filename
                        )
                        
                        if (aiResult && aiResult.ai_suggestions && Array.isArray(aiResult.ai_suggestions) && aiResult.ai_suggestions.length > 0) {
                            // Auto-select the best suggestion (highest relevance score)
                            const bestSuggestion = aiResult.ai_suggestions[0]
                            
                            // Determine source type based on the suggestion
                            let sourceType: 'workflow' | 'civitai' | 'hf' = 'hf'
                            if (bestSuggestion.source === 'workflow') {
                                sourceType = 'workflow'
                            } else if (bestSuggestion.civitai_file_id) {
                                sourceType = 'civitai'
                            }
                            
                            // Auto-resolve with the best suggestion
                            newResolvedModels.push({
                                filename: model.filename,
                                node_type: model.node_type,
                                dest_relative_path: model.dest_relative_path,
                                source: {
                                    type: sourceType,
                                    file_id: bestSuggestion.hf_file_id || bestSuggestion.civitai_file_id || null,
                                    url: bestSuggestion.download_url || bestSuggestion.url || null,
                                }
                            })
                            
                            totalResolved++
                            
                            // Merge AI suggestions with existing suggestions
                            return {
                                ...model,
                                suggestions: [
                                    ...aiResult.ai_suggestions.map(s => ({
                                        filename: s.filename,
                                        source: (s.source === 'civitai' ? 'civitai' : 'hf') as 'civitai' | 'hf',
                                        filepath: '',
                                        hf_file_id: s.hf_file_id || null,
                                        civitai_file_id: s.civitai_file_id || null,
                                        url: s.url,
                                        node_type: s.node_type,
                                        sha256_checksum: s.sha256_checksum || null,
                                    })),
                                    ...(model.suggestions || [])
                                ]
                            }
                        }
                        
                        return model
                    })
                    
                    setMissingModels(updatedMissingModels)
                    setResolvedMissingModels(prev => [...prev, ...newResolvedModels])
                    
                    if (totalResolved > 0) {
                        toast.success(`Auto-resolved ${totalResolved} models with AI suggestions`)
                        
                        // If all models are resolved, automatically proceed to import
                        if (totalResolved === detectedMissingModels.length) {
                            toast.success('All models resolved! Ready to import.')
                            setResolvedAllModels(true)
                        }
                    } else {
                        toast.info('No AI suggestions found. Please resolve models manually.')
                    }
                } else if (result && result.success && (!result.missing_models || result.missing_models.length === 0)) {
                    // No missing models found
                    toast.success('Workflow loaded successfully! No missing models.')
                } else {
                    console.log('[ImportWorkflowUI] Auto-resolve result:', result)
                    toast.info('Model auto-resolution completed.')
                }
            } catch (autoResolveError) {
                console.error('Error during auto-resolve:', autoResolveError)
                toast.error('Failed to auto-resolve models, but you can still import and resolve manually')
            }
            
        } catch (error) {
            console.error('Error importing from URL:', error)
            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
            toast.error(`Failed to import from URL: ${errorMessage}`)
            
            // Provide helpful error messages
            if (errorMessage.includes('fetch')) {
                toast.error('Could not fetch workflow from URL. Please check the URL and try again.')
            } else if (errorMessage.includes('JSON')) {
                toast.error('Invalid workflow format. Please ensure the URL points to a valid ComfyUI workflow JSON.')
            } else if (errorMessage.includes('valid')) {
                toast.error('The workflow appears to be invalid or corrupted.')
            }
            
            // Reset states on error
            setImportJson(undefined)
            setParsedWorkflow(null)
            setMissingModels([])
        } finally {
            setIsLoadingFromUrl(false)
        }
    }

    const validateWorkflowForMissingModels = async (workflowJson: any) => {
        try {
            console.log('Validating workflow for missing models...')
            const response = await fetch('/api/workflow/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ workflow_json: workflowJson }),
            })
            
            const result = await response.json()
            console.log('Workflow validation result:', result)
            
            if (result.error === 'MISSING_MODELS' && result.missing_models) {
                // Convert missing models to the expected format
                const formattedMissingModels: MissingModel[] = Array.isArray(result.missing_models)
                    ? result.missing_models.map((model: any) => ({
                        filename: model.filename || '',
                        node_type: model.node_type || 'unknown',
                        dest_relative_path: model.dest_relative_path || '',
                        suggestions: [] // Will be populated by auto-resolve if needed
                    }))
                    : [result.missing_models].map((model: any) => ({
                        filename: model.filename || '',
                        node_type: model.node_type || 'unknown',
                        dest_relative_path: model.dest_relative_path || '',
                        suggestions: []
                    }));
                console.log('Setting missing models:', formattedMissingModels)
                setMissingModels(formattedMissingModels)
                toast.info(`Found ${formattedMissingModels.length} missing models. You can resolve them before importing.`)
                
                // Force a small delay to ensure state update is processed
                setTimeout(() => {
                    console.log('Missing models state after update:', missingModels)
                }, 100)
            } else if (result.success || (result.missing_models && (Array.isArray(result.missing_models) ? result.missing_models.length : 1) === 0)) {
                // No missing models found
                console.log('No missing models found, clearing state')
                setMissingModels([])
                toast.success('All required models are available!')
            } else if (result.error) {
                console.error('Workflow validation error:', result.error)
                toast.error(`Workflow validation failed: ${result.error}`)
            }
        } catch (error) {
            console.error('Error validating workflow:', error)
            toast.error('Failed to validate workflow for missing models')
        }
    }

    const {
        acceptedFiles,
        getRootProps,
        getInputProps,
        isFocused,
        isDragAccept,
        isDragReject,
    } = useDropzone({ 
        onDrop, 
        accept: { 
            'application/json': ['.json'],
            'application/zip': ['.zip'],
            'application/x-zip-compressed': ['.zip']
        }, 
        maxFiles: 1 
    })

    const style = useMemo(
        () => ({
            ...baseStyle,
            ...(isFocused ? focusedStyle : {}),
            ...(isDragAccept ? acceptStyle : {}),
            ...(isDragReject ? rejectStyle : {}),
        }),
        [isFocused, isDragAccept, isDragReject]
    )

    useEffect(() => {
        // if settings are loaded and the ALLOW_OVERRIDABLE_PORTS_PER_PROJECT is set to false,
        // then we should not allow the user to specify a fixed port
        if (getSettingsQuery.data) {
            if (!getSettingsQuery.data.ALLOW_OVERRIDABLE_PORTS_PER_PROJECT) {
                setUseFixedPort(false)
            }
        }
    }, [getSettingsQuery.data])


    if (getSettingsQuery.isLoading) {
        return <div>Loading...</div>
    }

    return (
        <>
            <Dialog
                onOpenChange={(open) => setImportProjectDialogOpen(open)}
                open={importProjectDialogOpen}
            >
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Import project</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="name" className="text-right">
                                Name
                            </Label>
                            <Input
                                id="name"
                                placeholder=""
                                className="col-span-3"
                                value={projectName}
                                onChange={(e) => setProjectName(e.target.value)}
                            />
                        </div>

                        {(getSettingsQuery.data
                            ?.ALLOW_OVERRIDABLE_PORTS_PER_PROJECT === true) && (
                            <>
                                <div className="grid grid-cols-3 items-center gap-4">
                                    <Label
                                        htmlFor="useFixedPort"
                                        className="text-sm"
                                    >
                                        Use a static port
                                    </Label>
                                    <Checkbox
                                        id="useFixedPort"
                                        checked={useFixedPort}
                                        onCheckedChange={(checked) => {
                                            // @ts-ignore
                                            setUseFixedPort(checked)
                                        }}
                                    />
                                </div>
                                {useFixedPort && (
                                    <div className="grid grid-cols-4 items-center gap-4">
                                        <Label
                                            htmlFor="port"
                                            className="text-right"
                                        >
                                            Port
                                        </Label>
                                        <Input
                                            id="port"
                                            type="number"
                                            required={useFixedPort}
                                            min={getSettingsQuery.data.PROJECT_MIN_PORT}
                                            max={getSettingsQuery.data.PROJECT_MAX_PORT}
                                            placeholder=""
                                            // className="col-span-3"
                                            value={fixedPort}
                                            onChange={(e) =>
                                                setFixedPort(
                                                    parseInt(e.target.value)
                                                )
                                            }
                                        />
                                    </div>
                                )}
                                {useFixedPort && (
                                    <div className="grid grid-cols-1 items-center gap-4">
                                        <p className="text-xs text-neutral-500">
                                            If you're using Docker or running
                                            this on a remote server, make sure
                                            that the port number you chose
                                            satisfies any necessary
                                            port-forwarding rules.
                                        </p>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                    <DialogFooter>
                        <Button
                            type="submit"
                            onClick={(e) => {
                                e.preventDefault()
                                if (!importJson) return
                                importProjectMutation.mutate({
                                    import_json: importJson,
                                    name: projectName,
                                    useFixedPort,
                                    port: fixedPort,
                                })
                                setImportProjectDialogOpen(false)
                            }}
                        >
                            Import
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog
                onOpenChange={(open) => setProjectStatusDialogOpen(open)}
                open={projectStatusDialogOpen}
            >
                <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle>Importing project...</DialogTitle>
                        <DialogDescription className="mt-2">
                            Setting up ComfyUI, installing custom nodes,
                            downloading models. This might take a few minutes.
                            Do not close this page.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-6 py-4">
                        <div className="flex justify-center items-center">
                            <Loader2Icon className="animate-spin h-12 w-12 text-primary" />
                        </div>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">
                                    {importProgress?.message || 'Setting up environment...'}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                    {importProgress?.current && importProgress?.total
                                        ? `${importProgress.current}/${importProgress.total}`
                                        : 'Please wait'}
                                </span>
                            </div>
                            <Progress 
                                value={
                                    importProgress?.progress || 
                                    (importProgress?.current && importProgress?.total
                                        ? (importProgress.current / importProgress.total) * 100
                                        : 33)
                                } 
                                className="h-2" 
                            />
                            {importProgress?.type === 'download' && importProgress?.details?.filename && (
                                <p className="text-xs text-muted-foreground text-center">
                                    Downloading: {importProgress.details.filename}
                                </p>
                            )}
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <Dialog
                onOpenChange={(open) =>
                    setConfirmOnlyPartiallyResolvingOpen(open)
                }
                open={confirmOnlyPartiallyResolvingOpen}
            >
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>
                            Are you sure you want to skip resolving all models?
                        </DialogTitle>
                        <DialogDescription>
                            You will probably face errors when running the
                            workflow in ComfyUI and might have to upload
                            replacement models to run the workflow.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            onClick={(e) => {
                                e.preventDefault()
                                setConfirmOnlyPartiallyResolvingOpen(false)
                            }}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={(e) => {
                                e.preventDefault()
                                if (!importJson) return
                                importProjectMutation.mutate({
                                    import_json: importJson,
                                    name: projectName,
                                    partiallyResolved: true,
                                    useFixedPort,
                                    port: fixedPort,
                                })
                            }}
                        >
                            Yes, skip
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <div className="flex flex-col p-10">
                <div className="flex flex-col">
                    <h1 className="text-3xl font-semibold">Import workflow</h1>
                    <p className="mt-5 font-medium text-gray-700">
                        Drag & drop a <b>ComfyUI workflow json file</b>,{' '}
                        <b>ComfyUI Launcher json file</b>, or{' '}
                        <b>ZIP archive containing a workflow</b> to run it with{' '}
                        <b>ZERO setup</b>.
                    </p>
                </div>

                <div className="flex flex-col mt-10">
                    {/* @ts-ignore */}
                    <div
                        className={cn(
                            "relative overflow-hidden bg-card border-border",
                            "hover:border-primary/50 dark:bg-card/50"
                        )}
                        //  @ts-ignore
                        {...getRootProps({ style })}
                    >
                        <input {...getInputProps()} />
                        <div className="flex flex-col items-center justify-center space-y-4">
                            <UploadCloudIcon className="h-12 w-12 text-muted-foreground" />
                            <div className="text-center">
                                <p className="text-lg font-medium text-foreground">
                                    Drag & drop your workflow file here
                                </p>
                                <p className="text-sm text-muted-foreground mt-1">
                                    or click to browse
                                </p>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Supports ComfyUI workflow JSON files and ZIP archives
                            </p>
                        </div>
                    </div>
                    {acceptedFiles.length > 0 && (
                        <div className="mt-4 p-4 bg-card border border-border rounded-lg">
                            <div className="flex items-center gap-3">
                                {isZipFile ? (
                                    <FileArchiveIcon className="h-10 w-10 text-primary" />
                                ) : (
                                    <FileJsonIcon className="h-10 w-10 text-primary" />
                                )}
                                <div className="flex-1">
                                    {acceptedFiles.slice(0, 1).map((file) => (
                                        <div key={file.name}>
                                            <p className="font-medium text-sm text-foreground">
                                                {file.name}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                {(file.size / 1024).toFixed(2)} KB
                                                {isZipFile && ' - ZIP Archive'}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Import from URL Section */}
                <div className="mt-8 space-y-4">
                    <div className="flex items-center gap-2">
                        <div className="flex-1 h-px bg-border" />
                        <span className="text-sm text-muted-foreground px-2">OR</span>
                        <div className="flex-1 h-px bg-border" />
                    </div>
                    
                    <div className="space-y-3">
                        <div className="flex items-center gap-2">
                            <Link2Icon className="h-5 w-5 text-primary" />
                            <h3 className="text-lg font-semibold">Import from URL</h3>
                        </div>
                        
                        <div className="flex gap-2">
                            <Input
                                type="url"
                                placeholder="https://raw.githubusercontent.com/Comfy-Org/workflow_templates/..."
                                value={workflowUrl}
                                onChange={(e) => setWorkflowUrl(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        handleImportFromUrl()
                                    }
                                }}
                                className="flex-1"
                                disabled={isLoadingFromUrl}
                            />
                            <Button
                                onClick={handleImportFromUrl}
                                disabled={!workflowUrl || isLoadingFromUrl}
                                className="min-w-[140px]"
                            >
                                {isLoadingFromUrl ? (
                                    <>
                                        <Loader2Icon className="w-4 h-4 mr-2 animate-spin" />
                                        Loading...
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-4 h-4 mr-2" />
                                        Import & Auto-Resolve
                                    </>
                                )}
                            </Button>
                        </div>
                        
                        <p className="text-xs text-muted-foreground">
                            Enter a direct URL to a ComfyUI workflow JSON file. Models will be automatically resolved using AI.
                        </p>
                    </div>
                </div>

                {/* Workflow Preview */}
                {parsedWorkflow && (
                    <div className="mt-6">
                        <WorkflowPreview workflowData={parsedWorkflow} />
                    </div>
                )}
                
                {/* ZIP file notice */}
                {isZipFile && !parsedWorkflow && (
                    <div className="mt-6 p-4 bg-muted/50 border border-border rounded-lg">
                        <div className="flex items-start gap-3">
                            <FileArchiveIcon className="h-5 w-5 text-muted-foreground mt-0.5" />
                            <div>
                                <p className="text-sm font-medium">ZIP Archive Detected</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    The workflow and any included assets will be extracted during import.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {missingModels && Array.isArray(missingModels) && missingModels.length > 0 && (
                    <Card className="bg-[#0a0a0a] backdrop-blur-xl border-2 border-[#444] w-full">
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-white">
                                        {resolvedAllModels
                                            ? 'All unrecognized models have been resolved.'
                                            : 'These models were not recognized'}
                                    </CardTitle>
                                    <CardDescription className="text-[#999]">
                                        {resolvedAllModels
                                            ? 'Please try importing again.'
                                            : 'Replace missing models with the models that are available to avoid getting errors.'}
                                    </CardDescription>
                                </div>
                                {!resolvedAllModels && (
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={async () => {
                                            if (!parsedWorkflow) {
                                                toast.error('No workflow data available')
                                                return
                                            }
                                            
                                            setIsAutoResolving(true)
                                            setAutoResolveProgress('Searching for models...')
                                            
                                            try {
                                                const result = await apiClient.autoResolveModels(parsedWorkflow)
                                                
                                                if (result.error === 'MISSING_MODELS' && result.ai_search_enabled && result.missing_models) {
                                                    let totalResolved = 0
                                                    
                                                    // Update missing models with AI suggestions
                                                    const updatedMissingModels = (Array.isArray(missingModels) ? missingModels : []).map(model => {
                                                        const aiResult = result.missing_models?.find(
                                                            m => m.filename === model.filename
                                                        )
                                                        
                                                        if (aiResult && aiResult.ai_suggestions && Array.isArray(aiResult.ai_suggestions) && aiResult.ai_suggestions.length > 0) {
                                                            // Auto-select the best suggestion (highest relevance score)
                                                            const bestSuggestion = aiResult.ai_suggestions[0]
                                                            
                                                            // Determine source type based on the suggestion
                                                            let sourceType: 'workflow' | 'civitai' | 'hf' = 'hf'
                                                            if (bestSuggestion.source === 'workflow') {
                                                                sourceType = 'workflow'
                                                            } else if (bestSuggestion.civitai_file_id) {
                                                                sourceType = 'civitai'
                                                            }
                                                            
                                                            // Auto-resolve with the best suggestion
                                                            setResolvedMissingModels(prev => [
                                                                ...prev,
                                                                {
                                                                    filename: model.filename,
                                                                    node_type: model.node_type,
                                                                    dest_relative_path: model.dest_relative_path,
                                                                    source: {
                                                                        type: sourceType,
                                                                        file_id: bestSuggestion.hf_file_id || bestSuggestion.civitai_file_id || null,
                                                                        url: bestSuggestion.download_url || bestSuggestion.url || null,
                                                                    }
                                                                }
                                                            ])
                                                            
                                                            totalResolved++
                                                            
                                                            // Merge AI suggestions with existing suggestions
                                                            return {
                                                                ...model,
                                                                suggestions: [
                                                                    ...aiResult.ai_suggestions.map(s => ({
                                                                        filename: s.filename,
                                                                        source: (s.source === 'civitai' ? 'civitai' : 'hf') as 'civitai' | 'hf',
                                                                        filepath: '',
                                                                        hf_file_id: s.hf_file_id || null,
                                                                        civitai_file_id: s.civitai_file_id || null,
                                                                        url: s.url,
                                                                        node_type: s.node_type,
                                                                        sha256_checksum: s.sha256_checksum || null,
                                                                    })),
                                                                    ...model.suggestions
                                                                ]
                                                            }
                                                        }
                                                        
                                                        return model
                                                    })
                                                    
                                                    setMissingModels(updatedMissingModels)
                                                    
                                                    if (totalResolved > 0) {
                                                        toast.success(`Auto-resolved ${totalResolved} models with AI suggestions`)
                                                    } else {
                                                        toast.info('No models could be auto-resolved')
                                                    }
                                                } else {
                                                    toast.error('Failed to auto-resolve models')
                                                }
                                            } catch (error) {
                                                console.error('Error auto-resolving models:', error)
                                                toast.error('Failed to auto-resolve models')
                                            } finally {
                                                setIsAutoResolving(false)
                                                setAutoResolveProgress(null)
                                            }
                                        }}
                                        disabled={isAutoResolving}
                                        className="flex items-center gap-2"
                                    >
                                        {isAutoResolving ? (
                                            <>
                                                <Loader2Icon className="w-4 h-4 animate-spin" />
                                                {autoResolveProgress || 'Searching...'}
                                            </>
                                        ) : (
                                            <>
                                                <Sparkles className="w-4 h-4" />
                                                Auto Resolve All
                                            </>
                                        )}
                                    </Button>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="flex flex-col gap-6 space-y-5">
                            {missingModels && missingModels.length > 0 && missingModels.map((missing_model) => {
                                    //iterate through missingModels instead
                                    const isResolved = resolvedMissingModels && resolvedMissingModels.some(
                                        resolved => resolved.filename === missing_model.filename
                                    )
                                    const resolvedModel = resolvedMissingModels && resolvedMissingModels.find(
                                        resolved => resolved.filename === missing_model.filename
                                    )
                                return (
                                    <MissingModelItem
                                        key={`${missing_model.filename}_${missing_model.node_type}_${missing_model.dest_relative_path}`}
                                        missingModel={missing_model}
                                        resolveMutationToUse={
                                            resolveMissingModelMutationWithSuggestion
                                        }
                                        unResolveMutationToUse={
                                            unResolveMissingModelMutationWithSuggestion
                                        }
                                        isResolved={isResolved}
                                        resolvedModel={resolvedModel}
                                    />
                                )
                            })}
                        </CardContent>
                    </Card>
                )}

                <div className="mt-5">
                    <Button
                        variant="default"
                        disabled={!importJson}
                        onClick={(e) => {
                            e.preventDefault()
                            if (!importJson) return
                            if (
                                missingModels &&
                                missingModels.length > 0 &&
                                !resolvedAllModels
                            ) {
                                setConfirmOnlyPartiallyResolvingOpen(true)
                            } else {
                                setImportProjectDialogOpen(true)
                            }
                        }}
                    >
                        Import
                    </Button>
                </div>
            </div>
        </>
    )
}

export default ImportWorkflowUI
