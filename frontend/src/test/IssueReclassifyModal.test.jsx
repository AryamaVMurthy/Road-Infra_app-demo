import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { IssueReviewModal } from '../features/authority/components/Modals/IssueReviewModal'


describe('IssueReviewModal category assignment', () => {
  it('shows manual category assignment controls and submits an assignment request', () => {
    const onReclassify = vi.fn()

    render(
      <IssueReviewModal
        issue={{
          id: 'issue-1',
          status: 'REPORTED',
          category_name: null,
          category_id: null,
        }}
        issueTypes={[
          { id: 'cat-1', name: 'Pothole' },
          { id: 'cat-2', name: 'Drainage' },
        ]}
        onClose={() => {}}
        onApprove={() => {}}
        onReject={() => {}}
        onReclassify={onReclassify}
        submitting={false}
      />
    )

    expect(screen.getByText(/category assignment/i)).toBeInTheDocument()
    expect(screen.getByText(/spam/i)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/assign category/i), {
      target: { value: 'cat-2' },
    })
    fireEvent.change(screen.getByLabelText(/assignment reason/i), {
      target: { value: 'Manual review found drainage issue' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save category/i }))

    expect(onReclassify).toHaveBeenCalledWith('issue-1', 'cat-2', 'Manual review found drainage issue')
  })
})
