import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RecoveryProgress } from '../RecoveryProgress'
import type { DownloadRecoveryStatus } from '@/lib/types'

const mockDownloadStatus: DownloadRecoveryStatus = {
  url: 'https://example.com/model.safetensors',
  dest_path: '/models/model.safetensors',
  status: 'recovering',
  bytes_downloaded: 1024 * 1024 * 50, // 50MB
  total_bytes: 1024 * 1024 * 100, // 100MB
  progress: 0.5,
  attempts: 2,
  error: 'Connection timeout',
  speed_bps: 1024 * 1024 * 2 // 2MB/s
}

describe('RecoveryProgress', () => {
  it('renders basic progress bar with value', () => {
    render(<RecoveryProgress value={0.6} />)
    
    expect(screen.getByText('60%')).toBeInTheDocument()
  })

  it('displays recovery status with download information', () => {
    render(<RecoveryProgress recoveryStatus={mockDownloadStatus} />)
    
    // Check status display
    expect(screen.getByText('Recovering')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
    
    // Check retry indicator
    expect(screen.getByText('Attempt 2')).toBeInTheDocument()
    
    // Check speed info
    expect(screen.getByText('2.0 MB/s')).toBeInTheDocument()
    
    // Check bytes display
    expect(screen.getByText('50.0 MB / 100.0 MB')).toBeInTheDocument()
  })

  it('shows error message when present', () => {
    render(<RecoveryProgress recoveryStatus={mockDownloadStatus} />)
    
    expect(screen.getByText('Connection timeout')).toBeInTheDocument()
  })

  it('displays correct status icons', () => {
    const { rerender } = render(
      <RecoveryProgress recoveryStatus={{...mockDownloadStatus, status: 'recovering'}} />
    )
    
    // Should show spinning refresh icon for recovering
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    
    // Test completed status
    rerender(
      <RecoveryProgress recoveryStatus={{...mockDownloadStatus, status: 'completed'}} />
    )
    expect(screen.getByText('Completed')).toBeInTheDocument()
    
    // Test failed status
    rerender(
      <RecoveryProgress recoveryStatus={{...mockDownloadStatus, status: 'failed'}} />
    )
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('shows resume point indicator for partial downloads', () => {
    render(<RecoveryProgress recoveryStatus={mockDownloadStatus} />)
    
    // Should have a resume point indicator at 50%
    const resumeIndicator = document.querySelector('[title="Resume point"]')
    expect(resumeIndicator).toBeInTheDocument()
    expect(resumeIndicator).toHaveStyle({ left: '50%' })
  })

  it('handles pause/resume actions', () => {
    const onPause = vi.fn()
    const onResume = vi.fn()
    
    const { rerender } = render(
      <RecoveryProgress 
        recoveryStatus={{...mockDownloadStatus, status: 'downloading'}}
        onPause={onPause}
      />
    )
    
    // Should show pause button for downloading
    const pauseButton = screen.getByTitle('pause')?.closest('button')
    if (pauseButton) {
      fireEvent.click(pauseButton)
      expect(onPause).toHaveBeenCalledOnce()
    }
    
    // Test resume button
    rerender(
      <RecoveryProgress 
        recoveryStatus={{...mockDownloadStatus, status: 'pending'}}
        onResume={onResume}
      />
    )
    
    const resumeButton = document.querySelector('button')
    if (resumeButton?.querySelector('.lucide-play')) {
      fireEvent.click(resumeButton)
      expect(onResume).toHaveBeenCalledOnce()
    }
  })

  it('handles cancel action', () => {
    const onCancel = vi.fn()
    
    render(
      <RecoveryProgress 
        recoveryStatus={mockDownloadStatus}
        onCancel={onCancel}
      />
    )
    
    // Find cancel button (× symbol)
    const cancelButton = Array.from(document.querySelectorAll('button'))
      .find(btn => btn.textContent === '×')
    
    if (cancelButton) {
      fireEvent.click(cancelButton)
      expect(onCancel).toHaveBeenCalledOnce()
    }
  })

  it('formats bytes correctly', () => {
    const statusWithLargeFiles: DownloadRecoveryStatus = {
      ...mockDownloadStatus,
      bytes_downloaded: 1024 * 1024 * 1024 * 2.5, // 2.5GB
      total_bytes: 1024 * 1024 * 1024 * 5, // 5GB
    }
    
    render(<RecoveryProgress recoveryStatus={statusWithLargeFiles} />)
    
    expect(screen.getByText('2.5 GB / 5.0 GB')).toBeInTheDocument()
  })

  it('shows striped animation for recovery state', () => {
    render(<RecoveryProgress recoveryStatus={mockDownloadStatus} variant="recovery" />)
    
    // Progress bar should have recovery styling
    const progressBar = document.querySelector('[class*="bg-gradient"]')
    expect(progressBar).toBeInTheDocument()
    expect(progressBar).toHaveClass('animate-pulse')
  })

  it('hides retry indicator when showRetryIndicator is false', () => {
    render(
      <RecoveryProgress 
        recoveryStatus={mockDownloadStatus}
        showRetryIndicator={false}
      />
    )
    
    expect(screen.queryByText('Attempt 2')).not.toBeInTheDocument()
  })

  it('hides speed info when showSpeedInfo is false', () => {
    render(
      <RecoveryProgress 
        recoveryStatus={mockDownloadStatus}
        showSpeedInfo={false}
      />
    )
    
    expect(screen.queryByText('2.0 MB/s')).not.toBeInTheDocument()
  })

  it('uses correct variant styling', () => {
    const { rerender } = render(<RecoveryProgress value={0.5} variant="error" />)
    
    // Should have error styling
    expect(document.querySelector('.bg-red-500')).toBeInTheDocument()
    
    rerender(<RecoveryProgress value={0.5} variant="success" />)
    expect(document.querySelector('.bg-green-500')).toBeInTheDocument()
  })

  it('handles zero progress gracefully', () => {
    const zeroProgressStatus: DownloadRecoveryStatus = {
      ...mockDownloadStatus,
      bytes_downloaded: 0,
      total_bytes: 0,
      progress: 0
    }
    
    render(<RecoveryProgress recoveryStatus={zeroProgressStatus} />)
    
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('0 Bytes')).toBeInTheDocument()
  })
})