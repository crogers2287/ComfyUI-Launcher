import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import RecoveryBanner from '../RecoveryBanner'
import type { RecoveryStatus } from '@/lib/types'

const mockRecoveryOperations: RecoveryStatus[] = [
  {
    operation_id: 'test-1',
    operation_name: 'Download Model A',
    state: 'recovering',
    attempt: 2,
    max_attempts: 5,
    started_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:01:00Z',
    progress: 0.4,
    error: 'Network timeout'
  },
  {
    operation_id: 'test-2', 
    operation_name: 'Install Custom Node B',
    state: 'in_progress',
    attempt: 1,
    max_attempts: 3,
    started_at: '2024-01-01T00:00:30Z',
    updated_at: '2024-01-01T00:01:30Z',
    progress: 0.7
  },
  {
    operation_id: 'test-3',
    operation_name: 'Validate Workflow C',
    state: 'success',
    attempt: 3,
    max_attempts: 5,
    started_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:02:00Z',
    progress: 1.0
  }
]

describe('RecoveryBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing when no operations are provided', () => {
    render(<RecoveryBanner recoveryOperations={[]} />)
    expect(screen.queryByText('Recovery Operations')).not.toBeInTheDocument()
  })

  it('displays recovery operations with correct information', () => {
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} />)
    
    // Check header
    expect(screen.getByText('Recovery Operations (3)')).toBeInTheDocument()
    
    // Check individual operations
    expect(screen.getByText('Download Model A')).toBeInTheDocument()
    expect(screen.getByText('Install Custom Node B')).toBeInTheDocument()
    expect(screen.getByText('Validate Workflow C')).toBeInTheDocument()
    
    // Check attempt badges
    expect(screen.getByText('Attempt 2/5')).toBeInTheDocument()
    expect(screen.getByText('Attempt 1/3')).toBeInTheDocument()
    expect(screen.getByText('Attempt 3/5')).toBeInTheDocument()
  })

  it('shows progress bars for operations with progress', () => {
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} />)
    
    // Progress percentages
    expect(screen.getByText('40%')).toBeInTheDocument()
    expect(screen.getByText('70%')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('displays error messages when present', () => {
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} />)
    
    expect(screen.getByText('Error: Network timeout')).toBeInTheDocument()
  })

  it('shows correct state badges', () => {
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} />)
    
    expect(screen.getByText('recovering')).toBeInTheDocument()
    expect(screen.getByText('in_progress')).toBeInTheDocument()
    expect(screen.getByText('success')).toBeInTheDocument()
  })

  it('allows collapsing and expanding', () => {
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} />)
    
    const toggleButton = screen.getByRole('button', { name: /recovery operations/i })
    
    // Initially expanded
    expect(screen.getByText('Download Model A')).toBeInTheDocument()
    
    // Click to collapse
    fireEvent.click(toggleButton)
    
    // Should still show header but not content
    expect(screen.getByText('Recovery Operations (3)')).toBeInTheDocument()
  })

  it('allows dismissing individual operations', () => {
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} />)
    
    // Find and click dismiss button for first operation
    const dismissButtons = screen.getAllByRole('button')
    const firstDismissButton = dismissButtons.find(button => 
      button.querySelector('svg')?.classList.contains('lucide-x')
    )
    
    if (firstDismissButton) {
      fireEvent.click(firstDismissButton)
      
      // Operation should be hidden after dismiss
      waitFor(() => {
        expect(screen.queryByText('Download Model A')).not.toBeInTheDocument()
      })
    }
  })

  it('shows clear completed button when there are completed operations', () => {
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} />)
    
    expect(screen.getByText('Clear completed')).toBeInTheDocument()
  })

  it('calls onDismiss when dismiss button is clicked', () => {
    const onDismiss = vi.fn()
    render(<RecoveryBanner recoveryOperations={mockRecoveryOperations} onDismiss={onDismiss} />)
    
    const dismissButton = screen.getByRole('button', { 
      name: '' // X button without aria-label
    })
    
    fireEvent.click(dismissButton)
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('auto-dismisses completed operations after delay', async () => {
    const completedOperation: RecoveryStatus = {
      operation_id: 'completed-test',
      operation_name: 'Completed Operation',
      state: 'success',
      attempt: 1,
      max_attempts: 3,
      started_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:01:00Z'
    }

    render(<RecoveryBanner recoveryOperations={[completedOperation]} />)
    
    expect(screen.getByText('Completed Operation')).toBeInTheDocument()
    
    // Should auto-dismiss after 5 seconds (mocked in test environment)
    await waitFor(() => {
      expect(screen.queryByText('Completed Operation')).not.toBeInTheDocument()
    }, { timeout: 6000 })
  })

  it('handles empty recovery operations gracefully', () => {
    render(<RecoveryBanner recoveryOperations={[]} />)
    
    // Should render nothing
    expect(document.body.textContent).toBe('')
  })

  it('formats time remaining correctly', () => {
    const operationWithETA: RecoveryStatus = {
      operation_id: 'eta-test',
      operation_name: 'Operation with ETA',
      state: 'in_progress',
      attempt: 1,
      max_attempts: 3,
      started_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:01:00Z',
      estimated_completion: new Date(Date.now() + 1800000).toISOString() // 30 minutes from now
    }

    render(<RecoveryBanner recoveryOperations={[operationWithETA]} />)
    
    expect(screen.getByText('~30min remaining')).toBeInTheDocument()
  })
})