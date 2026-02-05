import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AcceptTaskModal } from '../features/worker/components/Modals/AcceptTaskModal'

describe('AcceptTaskModal', () => {
  const baseTask = { id: 'task-1', category_name: 'Pothole' }

  it('renders modal content when task is provided', () => {
    render(
      <AcceptTaskModal
        task={baseTask}
        eta=""
        onEtaChange={vi.fn()}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )

    expect(screen.getByText('Task Acceptance')).toBeInTheDocument()
    expect(screen.getByText(/ID: task-1/i)).toBeInTheDocument()
  })

  it('emits selected date when quick date is chosen', () => {
    const onEtaChange = vi.fn()
    render(
      <AcceptTaskModal
        task={baseTask}
        eta=""
        onEtaChange={onEtaChange}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )

    fireEvent.click(screen.getByText('Tomorrow'))
    expect(onEtaChange).toHaveBeenCalledTimes(1)
    expect(onEtaChange.mock.calls[0][0]).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('disables confirm button without ETA', () => {
    render(
      <AcceptTaskModal
        task={baseTask}
        eta=""
        onEtaChange={vi.fn()}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )

    const confirmButton = screen.getByText('Confirm & Accept')
    expect(confirmButton).toBeDisabled()
  })
})
