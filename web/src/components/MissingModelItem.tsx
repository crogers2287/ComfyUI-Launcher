'use client'

import {
    Loader2Icon,
    AlertTriangle,
    Replace,
    CheckCircle,
    InfoIcon,
    ChevronsUpDown,
    Fingerprint,
    Search,
    Sparkles,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { UseMutationResult } from '@tanstack/react-query'
import { Button } from './ui/button'
import { MissingModel, Source, Suggestion, ResolvedMissingModelFile } from '@/lib/types'
import { Separator } from './ui/separator'
import { Badge } from './ui/badge'
import HFLogo from './HFLogo'
import { toast } from 'sonner'
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { apiClient } from '@/lib/api'

function MissingModelItem({
    missingModel,
    resolveMutationToUse,
    unResolveMutationToUse,
    isResolved = false,
    resolvedModel,
}: {
    missingModel: MissingModel
    resolveMutationToUse: UseMutationResult<
        void,
        Error,
        {
            filename: string
            node_type: string
            dest_relative_path: string
            source: Source
        },
        unknown
    >
    unResolveMutationToUse: UseMutationResult<
        void,
        Error,
        { filename: string },
        unknown
    >
    isResolved?: boolean
    resolvedModel?: ResolvedMissingModelFile
}) {
    const [loading, setLoading] = useState(false)
    const [resolved, setResolved] = useState(isResolved)
    const [newFileName, setNewFileName] = useState('')
    const [isOpen, setIsOpen] = useState(true)
    const [isSearching, setIsSearching] = useState(false)
    const [aiSuggestions, setAiSuggestions] = useState<Suggestion[]>([])

    // Update resolved state when prop changes
    useEffect(() => {
        setResolved(isResolved)
        if (isResolved && resolvedModel) {
            // Find the suggestion that matches the resolved model
            const matchingSuggestion = missingModel.suggestions.find(s => 
                (s.url === resolvedModel.source.url) ||
                (s.hf_file_id === resolvedModel.source.file_id) ||
                (s.civitai_file_id === resolvedModel.source.file_id)
            )
            if (matchingSuggestion) {
                setNewFileName(matchingSuggestion.filename)
            } else {
                // If no matching suggestion, use the original filename
                setNewFileName(missingModel.filename)
            }
        }
    }, [isResolved, resolvedModel, missingModel])

    if (!resolved) {
        return (
            <Collapsible
                open={isOpen}
                onOpenChange={setIsOpen}
                className="w-full flex flex-col items-start space-y-4"
            >
                <div className="w-full flex items-center justify-between space-x-4">
                    <div className="w-full flex flex-row items-center justify-between">
                        <div className="flex flex-row items-center gap-2">
                            {loading ? (
                                <Loader2Icon className=" text-orange-500 animate-spin w-5 h-5" />
                            ) : (
                                <AlertTriangle className="w-5 h-5 text-red-500" />
                            )}
                            <h3 className="text-white text-lg font-bold">
                                {missingModel.filename}
                            </h3>
                            <Badge className="flex flex-row items-center gap-2">
                                <InfoIcon className="w-4 h-4" />
                                {missingModel.node_type}
                            </Badge>
                        </div>
                    </div>
                    <div className="flex flex-row items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={async () => {
                                setIsSearching(true)
                                try {
                                    const result = await apiClient.findModel({
                                        filename: missingModel.filename,
                                        model_type: missingModel.node_type
                                    })
                                    
                                    if (result.success && result.results.length > 0) {
                                        // Convert AI results to Suggestion format
                                        const newSuggestions: Suggestion[] = result.results.map(r => ({
                                            filename: r.filename,
                                            source: r.source === 'civitai' ? 'civitai' : 'hf',
                                            filepath: '',
                                            hf_file_id: r.source === 'huggingface' ? (r.metadata?.path || null) : null,
                                            civitai_file_id: r.source === 'civitai' ? (r.metadata?.file_id || null) : null,
                                            url: r.url,
                                            node_type: r.model_type || missingModel.node_type,
                                            sha256_checksum: r.sha256_checksum || null,
                                        }))
                                        
                                        setAiSuggestions(newSuggestions)
                                        toast.success(`Found ${result.results.length} AI suggestions`)
                                        setIsOpen(true)
                                    } else {
                                        toast.error('No AI suggestions found')
                                    }
                                } catch (error) {
                                    console.error('Error searching for model:', error)
                                    toast.error('Failed to search for model')
                                } finally {
                                    setIsSearching(false)
                                }
                            }}
                            disabled={isSearching}
                            className="flex flex-row items-center gap-2"
                        >
                            {isSearching ? (
                                <Loader2Icon className="w-4 h-4 animate-spin" />
                            ) : (
                                <Search className="w-4 h-4" />
                            )}
                            Auto Find
                        </Button>
                        <CollapsibleTrigger asChild>
                            <Button className="flex flex-row items-center gap-2">
                                <ChevronsUpDown className="h-4 w-4" />
                                {isOpen ? 'hide suggestions' : 'show suggestions'}
                                <span className="sr-only">Toggle</span>
                            </Button>
                        </CollapsibleTrigger>
                    </div>
                </div>
                {/* below stuff that u wanna render outside of suggestions */}
                <CollapsibleContent className="space-y-2 w-full">
                    <div className="w-full flex flex-col items-start gap-4">
                        <div className="w-full flex flex-col items-start gap-4">
                            <div className="w-full flex flex-col items-start gap-">
                                <div className="flex flex-row items-center gap-2">
                                    <Replace className="w-4 h-4 text-green-400" />
                                    <h4 className="text-white text-md font-semibold">
                                        Replace with
                                    </h4>
                                </div>
                                
                                {/* AI Suggestions */}
                                {aiSuggestions && aiSuggestions.length > 0 && (
                                    <>
                                        <div className="flex flex-row items-center gap-2 mt-4 mb-2">
                                            <Sparkles className="w-4 h-4 text-purple-400" />
                                            <h5 className="text-white text-sm font-semibold">
                                                AI-Powered Suggestions
                                            </h5>
                                            <Badge variant="secondary" className="text-xs">
                                                {aiSuggestions.length} found
                                            </Badge>
                                        </div>
                                        {aiSuggestions.map((suggestion, idx) => {
                                            return (
                                                <div
                                                    key={`ai_${idx}_${suggestion.civitai_file_id}_${suggestion.hf_file_id}`}
                                                    className="w-full flex flex-row items-center my-1 pl-4"
                                                >
                                                    <Button
                                                        size="sm"
                                                        className="border border-purple-500/30 shadow-sm shadow-purple-400/20 mr-3"
                                                        onClick={async (e) => {
                                                            e.preventDefault()
                                                            setLoading(true)
                                                            try {
                                                                const mutation =
                                                                    await resolveMutationToUse.mutateAsync(
                                                                        {
                                                                            filename:
                                                                                missingModel.filename,
                                                                            node_type:
                                                                                missingModel.node_type,
                                                                            dest_relative_path:
                                                                                missingModel.dest_relative_path,
                                                                            source: {
                                                                                type: suggestion.civitai_file_id
                                                                                    ? 'civitai'
                                                                                    : 'hf',
                                                                                file_id:
                                                                                    suggestion.hf_file_id ||
                                                                                    suggestion.civitai_file_id,
                                                                                url: null,
                                                                            },
                                                                        }
                                                                    )
                                                                console.log(
                                                                    'mutation:',
                                                                    mutation
                                                                )
                                                                setNewFileName(
                                                                    suggestion.filename
                                                                )
                                                                setResolved(true)
                                                            } catch (error: unknown) {
                                                                toast.error(
                                                                    'there was an error when selecting the suggestion, please try again!'
                                                                )
                                                            } finally {
                                                                setLoading(false)
                                                            }
                                                        }}
                                                    >
                                                        Select
                                                    </Button>
                                                    <div className="flex flex-row items-center space-x-3">
                                                        {suggestion.source ===
                                                        'civitai' ? (
                                                            <img
                                                                alt={`civitai logo for model ${suggestion.filename}`}
                                                                src="/civitai-logo-github.png"
                                                                className="ph-no-capture w-5 h-5"
                                                            />
                                                        ) : (
                                                            <HFLogo className="w-5 h-5" />
                                                        )}
                                                        <a
                                                            href={suggestion.url}
                                                            target="_blank"
                                                        >
                                                            <p className="text-white text-sm font-medium underline decoration-dotted">
                                                                {suggestion.filename}
                                                            </p>
                                                        </a>
                                                        <Badge className="flex flex-row items-center gap-2">
                                                            <InfoIcon className="w-4 h-4" />
                                                            {suggestion.node_type}
                                                        </Badge>
                                                        {suggestion.sha256_checksum && (
                                                            <Badge className="flex flex-row items-center gap-2">
                                                                <Fingerprint className="w-4 h-4" />
                                                                {`sha256: ${suggestion.sha256_checksum?.slice(
                                                                    0,
                                                                    6
                                                                )}...`}
                                                            </Badge>
                                                        )}
                                                        <Badge variant="secondary" className="text-xs">
                                                            AI Found
                                                        </Badge>
                                                    </div>
                                                </div>
                                            )
                                        })}
                                        {missingModel.suggestions.length > 0 && (
                                            <Separator className="bg-[#666] my-3" />
                                        )}
                                    </>
                                )}
                                
                                {/* Original Suggestions */}
                                {missingModel.suggestions && missingModel.suggestions.length > 0 && (
                                    <div className="flex flex-row items-center gap-2 mt-2 mb-2">
                                        <h5 className="text-white text-sm font-semibold">
                                            Default Suggestions
                                        </h5>
                                    </div>
                                )}
                                {missingModel.suggestions && missingModel.suggestions.map((suggestion) => {
                                    return (
                                        <div
                                            key={`${suggestion.civitai_file_id}_${suggestion.hf_file_id}`}
                                            className="w-full flex flex-row items-center  my-1"
                                        >
                                            <Button
                                                size="sm"
                                                className="border border-[#222] shadow-sm shadow-[#fff] mr-3"
                                                // variant='secondary'
                                                onClick={async (e) => {
                                                    e.preventDefault()
                                                    setLoading(true)
                                                    try {
                                                        const mutation =
                                                            await resolveMutationToUse.mutateAsync(
                                                                {
                                                                    filename:
                                                                        missingModel.filename,
                                                                    node_type:
                                                                        missingModel.node_type,
                                                                    dest_relative_path:
                                                                        missingModel.dest_relative_path,
                                                                    source: {
                                                                        type: suggestion.civitai_file_id
                                                                            ? 'civitai'
                                                                            : 'hf',
                                                                        file_id:
                                                                            suggestion.hf_file_id ||
                                                                            suggestion.civitai_file_id,
                                                                        url: null,
                                                                    },
                                                                }
                                                            )
                                                        // resolveMutationToUse.mutate({ filename: missingModel.filename, node_type: missingModel.node_type, source: { type: suggestion.civitai_file_id ? "civitai" : "hf",  file_id: suggestion.hf_file_id || suggestion.civitai_file_id, url: null } })
                                                        console.log(
                                                            'mutation:',
                                                            mutation
                                                        )
                                                        setNewFileName(
                                                            suggestion.filename
                                                        )
                                                        setResolved(true)
                                                    } catch (error: unknown) {
                                                        toast.error(
                                                            'there was an error when selecting the suggestion, please try again!'
                                                        )
                                                    } finally {
                                                        setLoading(false)
                                                    }
                                                }}
                                            >
                                                Select
                                            </Button>
                                            <div className="flex flex-row   items-center space-x-3">
                                                {suggestion.source ===
                                                'civitai' ? (
                                                    <img
                                                        alt={`civitai logo for model ${suggestion.filename}`}
                                                        src="/civitai-logo-github.png"
                                                        className="ph-no-capture w-5 h-5"
                                                    />
                                                ) : (
                                                    <HFLogo className="w-5 h-5" />
                                                )}
                                                <a
                                                    href={suggestion.url}
                                                    target="_blank"
                                                >
                                                    <p className="text-white text-sm font-medium underline decoration-dotted">
                                                        {suggestion.filename}
                                                    </p>
                                                </a>
                                                <Badge className="flex flex-row items-center gap-2">
                                                    <InfoIcon className="w-4 h-4" />
                                                    {suggestion.node_type}
                                                </Badge>
                                                {suggestion.sha256_checksum && (
                                                    <Badge className="flex flex-row items-center gap-2">
                                                        <Fingerprint className="w-4 h-4" />
                                                        {`sha256: ${suggestion.sha256_checksum?.slice(
                                                            0,
                                                            6
                                                        )}...`}
                                                    </Badge>
                                                )}
                                            </div>
                                            <div className="flex flex-row items-center gap-2"></div>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                        <Separator className="bg-[#444]" />
                    </div>
                </CollapsibleContent>
            </Collapsible>
        )
    } else {
        return (
            <div className="w-full flex flex-row items-center justify-between">
                <div className="flex flex-row items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    <h3 className="text-white font-bold">{newFileName}</h3>
                    <h3 className="text-[#999] font-bold line-through ml-2">
                        {missingModel.filename}
                    </h3>
                </div>
                <Button
                    size="sm"
                    onClick={async (e) => {
                        e.preventDefault()
                        setLoading(true)
                        try {
                            const mutation =
                                await unResolveMutationToUse.mutateAsync({
                                    filename: missingModel.filename,
                                })
                            // unResolveMutationToUse.mutate({ filename: missingModel.filename })
                            console.log('mutation:', mutation)
                            setResolved(false)
                            setNewFileName('')
                        } catch (error: unknown) {
                            toast.error(
                                'something went wrong when attempting to edit your model. please try again.'
                            )
                        } finally {
                            setLoading(false)
                        }
                    }}
                >
                    Edit
                </Button>
            </div>
        )
    }
}

export default MissingModelItem
