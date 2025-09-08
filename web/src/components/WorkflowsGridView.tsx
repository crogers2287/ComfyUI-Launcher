'use client'

import { Project, Settings, ProjectRecoveryInfo } from '@/lib/types'
import { useQuery } from '@tanstack/react-query'
import { Masonry } from 'masonic'
import ProjectCard from './ProjectCard'
import { SearchInput } from './ui/search-input'
import { Button } from './ui/button'
import { ArrowDownIcon, ArrowUpIcon, CalendarIcon, TextIcon } from 'lucide-react'
import { useState, useMemo, useEffect } from 'react'
import { StorageIndicator } from './StorageIndicator'
import { useGlobalRecovery } from '@/hooks/use-recovery-socket'

function WorkflowsGridView() {
    const [searchQuery, setSearchQuery] = useState('')
    const [sortBy, setSortBy] = useState<'name' | 'date'>('date')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
    const [projectRecoveryInfo, setProjectRecoveryInfo] = useState<Map<string, ProjectRecoveryInfo>>(new Map())
    
    const { recoveryOperations } = useGlobalRecovery()

    // Update project recovery info based on recovery operations
    useEffect(() => {
        const newRecoveryInfo = new Map<string, ProjectRecoveryInfo>()
        
        recoveryOperations.forEach(operation => {
            // Extract project ID from operation ID if possible
            const projectIdMatch = operation.operation_id.match(/^([^_]+)_/)
            const projectId = projectIdMatch ? projectIdMatch[1] : 'global'
            
            const existing = newRecoveryInfo.get(projectId) || {
                project_id: projectId,
                active_operations: [],
                total_attempts: 0,
                last_recovery_at: undefined
            }
            
            // Update active operations
            const activeOps = existing.active_operations.filter(op => op.operation_id !== operation.operation_id)
            if (operation.state === 'recovering' || operation.state === 'in_progress') {
                activeOps.push(operation)
            }
            
            newRecoveryInfo.set(projectId, {
                ...existing,
                active_operations: activeOps,
                total_attempts: existing.total_attempts + (operation.attempt > 1 ? 1 : 0),
                last_recovery_at: operation.updated_at
            })
        })
        
        setProjectRecoveryInfo(newRecoveryInfo)
    }, [recoveryOperations])

    const getProjectsQuery = useQuery({
        queryKey: ['projects'],
        queryFn: async () => {
            const response = await fetch(`/api/projects`)
            const data = (await response.json()) as Project[]
            return data
        },
        refetchInterval: 10_000, // refetch every 10 seconds
    })

    const getSettingsQuery = useQuery({
        queryKey: ['settings'],
        queryFn: async () => {
            const response = await fetch(`/api/settings`)
            const data = await response.json()
            return data as Settings
        },
    })

    // Filter and sort projects - must be before any conditional returns
    const filteredAndSortedProjects = useMemo(() => {
        if (!getProjectsQuery.data) return []
        
        let filtered = getProjectsQuery.data

        // Filter by search query
        if (searchQuery) {
            filtered = filtered.filter(project => 
                project.state.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                project.id.toLowerCase().includes(searchQuery.toLowerCase())
            )
        }

        // Sort projects
        const sorted = [...filtered].sort((a, b) => {
            if (sortBy === 'name') {
                const nameA = a.state.name.toLowerCase()
                const nameB = b.state.name.toLowerCase()
                return sortOrder === 'asc' ? 
                    nameA.localeCompare(nameB) : 
                    nameB.localeCompare(nameA)
            }
            // Sort by date (using ID as proxy for creation date)
            return sortOrder === 'asc' ? 
                a.id.localeCompare(b.id) : 
                b.id.localeCompare(a.id)
        })

        return sorted
    }, [getProjectsQuery.data, searchQuery, sortBy, sortOrder])

    if (getProjectsQuery.isError || getSettingsQuery.isError) {
        return <div>Something went wrong, please refresh the page.</div>
    }

    if (getProjectsQuery.isLoading || getSettingsQuery.isLoading) {
        return <div>Loading...</div>
    }
    
    if (!getSettingsQuery.data || !getProjectsQuery.data || getProjectsQuery.data.length === 0) {
        return <></>
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between gap-4 flex-wrap">
                <SearchInput 
                    placeholder="Search projects..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="max-w-sm"
                />
                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1">
                        <Button
                            variant={sortBy === 'name' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => {
                                if (sortBy === 'name') {
                                    setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
                                } else {
                                    setSortBy('name')
                                    setSortOrder('asc')
                                }
                            }}
                            className="flex items-center gap-1"
                        >
                            <TextIcon className="h-4 w-4" />
                            Name
                            {sortBy === 'name' && (
                                sortOrder === 'asc' ? 
                                <ArrowUpIcon className="h-4 w-4" /> : 
                                <ArrowDownIcon className="h-4 w-4" />
                            )}
                        </Button>
                        <Button
                            variant={sortBy === 'date' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => {
                                if (sortBy === 'date') {
                                    setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
                                } else {
                                    setSortBy('date')
                                    setSortOrder('desc')
                                }
                            }}
                            className="flex items-center gap-1"
                        >
                            <CalendarIcon className="h-4 w-4" />
                            Date
                            {sortBy === 'date' && (
                                sortOrder === 'asc' ? 
                                <ArrowUpIcon className="h-4 w-4" /> : 
                                <ArrowDownIcon className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                    <StorageIndicator />
                </div>
            </div>
            
            {filteredAndSortedProjects.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                    No projects found matching "{searchQuery}"
                </div>
            ) : (
                <Masonry
                    key={filteredAndSortedProjects.map((p) => p.id).join(',')}
                    itemKey={(item, index) =>
                        item === undefined ? index : item.id
                    }
                    columnGutter={20}
                    columnWidth={350}
                    items={filteredAndSortedProjects}
                    render={(props) => (
                        <ProjectCard 
                            settings={getSettingsQuery.data} 
                            item={props.data}
                            recoveryInfo={projectRecoveryInfo.get(props.data.id)}
                        />
                    )}
                />
            )}
        </div>
    )
}

export default WorkflowsGridView
