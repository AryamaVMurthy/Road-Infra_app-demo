import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ReportIssue from '../pages/citizen/ReportIssue'


const navigateMock = vi.fn()
const postMock = vi.fn()

vi.mock('../services/api', () => ({
  default: {
    post: (...args) => postMock(...args),
  },
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigateMock,
}))

vi.mock('../hooks/useGeolocation', () => ({
  useGeolocation: () => ({
    loading: false,
    position: { lat: 17.4447, lng: 78.3483 },
  }),
}))

vi.mock('../components/InteractiveMap', () => ({
  InteractiveMap: ({ children }) => <div data-testid="mock-map">{children}</div>,
  Marker: () => <div data-testid="mock-marker" />,
}))


describe('ReportIssue VLM flow', () => {
  beforeEach(() => {
    navigateMock.mockReset()
    postMock.mockReset()
    global.URL.createObjectURL = vi.fn(() => 'blob:preview')
  })

  it('removes manual category selection and shows assigned category on success', async () => {
    postMock.mockResolvedValue({
      data: {
        issue_id: 'issue-1',
        submission_id: 'submission-1',
        category_id: null,
        category_name: null,
        requires_admin_category_assignment: true,
        duplicate_merged: false,
        message: 'Report submitted successfully',
      },
    })

    render(<ReportIssue />)

    expect(screen.queryByText(/incident category/i)).not.toBeInTheDocument()

    const file = new File(['photo'], 'report.jpg', { type: 'image/jpeg' })
    fireEvent.change(screen.getByLabelText(/tap to capture/i), {
      target: { files: [file] },
    })

    fireEvent.click(screen.getByRole('button', { name: /continue to location/i }))
    fireEvent.click(await screen.findByRole('button', { name: /broadcast report/i }))

    await waitFor(() =>
      expect(screen.getByText(/accepted for review/i)).toBeInTheDocument()
    )
  })

  it('shows generic rejection message when intake screening rejects the image', async () => {
    postMock.mockRejectedValue({
      response: {
        status: 422,
        data: {
          submission_id: 'submission-2',
          message: 'Report rejected by intake screening',
        },
      },
    })

    render(<ReportIssue />)

    const file = new File(['photo'], 'report.jpg', { type: 'image/jpeg' })
    fireEvent.change(screen.getByLabelText(/tap to capture/i), {
      target: { files: [file] },
    })

    fireEvent.click(screen.getByRole('button', { name: /continue to location/i }))
    fireEvent.click(await screen.findByRole('button', { name: /broadcast report/i }))

    await waitFor(() =>
      expect(screen.getByText(/rejected by intake screening/i)).toBeInTheDocument()
    )
  })
})
