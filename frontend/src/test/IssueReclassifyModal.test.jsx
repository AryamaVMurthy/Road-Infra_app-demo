import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { IssueReviewModal } from '../features/authority/components/Modals/IssueReviewModal'


describe('IssueReviewModal reclassification', () => {
  it('shows AI classification metadata and submits a reclassification request', () => {
    const onReclassify = vi.fn()

    render(
      <IssueReviewModal
        issue={{
          id: 'issue-1',
          status: 'REPORTED',
          category_name: 'Pothole',
          category_id: 'cat-1',
          classification_model_id: 'LiquidAI/LFM2.5-VL-1.6B-GGUF',
          classification_confidence: 0.91,
          classification_prompt_version: 'v1',
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

    expect(screen.getByText(/ai classification/i)).toBeInTheDocument()
    expect(screen.getByText(/LiquidAI\/LFM2.5-VL-1.6B-GGUF/i)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/reclassify category/i), {
      target: { value: 'cat-2' },
    })
    fireEvent.change(screen.getByLabelText(/reclassification reason/i), {
      target: { value: 'Manual review found drainage issue' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save reclassification/i }))

    expect(onReclassify).toHaveBeenCalledWith('issue-1', 'cat-2', 'Manual review found drainage issue')
  })
})
