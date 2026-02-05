import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ResolveTaskModal } from '../features/worker/components/Modals/ResolveTaskModal'

describe('ResolveTaskModal', () => {
  const baseProps = {
    task: { id: 'task-2', category_name: 'Drainage' },
    photo: null,
    onPhotoChange: vi.fn(),
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    isOnline: true,
    isResolving: false,
    etaDate: '',
    onEtaDateChange: vi.fn(),
  }

  it('renders step 1 by default', () => {
    render(<ResolveTaskModal {...baseProps} />)
    expect(screen.getByText('Set Completion Date')).toBeInTheDocument()
    expect(screen.getByText('Next: Upload Photo')).toBeInTheDocument()
  })

  it('blocks next step until ETA is chosen', () => {
    render(<ResolveTaskModal {...baseProps} />)
    const nextButton = screen.getByText('Next: Upload Photo')
    expect(nextButton).toBeDisabled()
  })

  it('moves to upload step after selecting ETA', () => {
    const props = { ...baseProps, etaDate: '2030-01-01' }
    render(<ResolveTaskModal {...props} />)

    const nextButton = screen.getByText('Next: Upload Photo')
    fireEvent.click(nextButton)

    expect(screen.getByText('Upload Proof')).toBeInTheDocument()
  })
})
