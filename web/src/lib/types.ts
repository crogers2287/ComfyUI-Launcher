export type WorkflowTemplateId =
    | 'empty'
    | 'animate_diff'
    | 'svd'
    | 'upscale'
    | 'img2img'
    | 'vid2vid'
    | 'img2vid'

export type WorkflowTemplateItem = {
    id: WorkflowTemplateId
    title: string
    description: string
    thumbnail: string
    isThumbnailVideo?: boolean
    credits?: string
}

export type Config = {
    credentials: {
        civitai: {
            apikey: string
        }
    }
}

export type Settings = {
    PROJECT_MIN_PORT: number,
    PROJECT_MAX_PORT: number,
    ALLOW_OVERRIDABLE_PORTS_PER_PROJECT: boolean,
    PROXY_MODE: boolean
}

export type ProjectState = {
    state:
        | 'install_comfyui'
        | 'install_custom_nodes'
        | 'download_files'
        | 'ready'
        | 'download_comfyui'
        | 'running'
    status_message: string
    port?: number | null
    pid?: number | null
    id: string
    name: string
}

export type Project = {
    id: string
    state: ProjectState
    project_folder_name: string
    project_folder_path: string
    last_modified: number
}

export type Suggestion = {
    filename: string
    source: 'hf' | 'civitai'
    filepath: string
    hf_file_id: string | number | null
    civitai_file_id: string | number | null
    url: string
    node_type: string
    sha256_checksum: string | null | undefined
}

export type Source = {
    type: 'hf' | 'civitai' | 'workflow'
    url: string | null
    file_id: string | number | null
}

export type MissingModel = {
    filename: string
    node_type: string
    suggestions: Suggestion[]
    dest_relative_path: string
    // backup_models: { id: string, file_name: string, link: string, type: string }[],
    // resolved: boolean,
    // new_file_name: string
}

export type ResolvedMissingModelFile = {
    filename: string
    node_type: string
    dest_relative_path: string
    source: Source
}

// Download Management Types for Issue #12
export type DownloadStatus = 'pending' | 'downloading' | 'paused' | 'completed' | 'failed' | 'cancelled'

export type DownloadInfo = {
    id: string
    url: string
    dest_path: string
    status: DownloadStatus
    progress: number
    bytes_downloaded: number
    total_bytes: number
    speed: number
    eta: number
    attempts: number
    error?: string
    created_at: string
    updated_at: string
    can_resume: boolean
    can_pause: boolean
}

export type DownloadSettings = {
    max_concurrent_downloads: number
    max_retries: number
    chunk_size: number
    timeout: number
    bandwidth_limit: number
    auto_resume: boolean
    verify_checksums: boolean
}

export type DownloadHistoryItem = {
    id: string
    url: string
    dest_path: string
    status: DownloadStatus
    bytes_downloaded: number
    total_bytes: number
    completed_at: string
    duration: number
    speed_avg: number
}
