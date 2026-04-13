import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminDashboard from '../pages/admin/AdminDashboard'

const navigateMock = vi.fn()
const apiGetMock = vi.fn()
const getAuthoritiesMock = vi.fn()
const getIssueTypesMock = vi.fn()
const getIntakeArchiveMock = vi.fn()

vi.mock('../services/api', () => ({
  API_URL: '/api/v1',
  default: {
    get: (...args) => apiGetMock(...args),
  },
}))

vi.mock('../services/admin', () => ({
  default: {
    getAuthorities: (...args) => getAuthoritiesMock(...args),
    getIssueTypes: (...args) => getIssueTypesMock(...args),
    getIntakeArchive: (...args) => getIntakeArchiveMock(...args),
  },
}))

vi.mock('../services/auth', () => ({
  authService: {
    logout: vi.fn(),
  },
}))

vi.mock('../hooks/useAutoRefresh', () => ({
  useAutoRefresh: vi.fn(),
}))

vi.mock('../components/MapboxDrawControl', () => ({
  default: () => <div data-testid="mapbox-draw-control" />,
}))

vi.mock('../components/InteractiveMap', () => ({
  InteractiveMap: ({ children }) => <div data-testid="interactive-map">{children}</div>,
  Marker: () => <div data-testid="interactive-marker" />,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

describe('Admin archive tab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiGetMock.mockResolvedValue({ data: { summary: {} } })
    getAuthoritiesMock.mockResolvedValue({ data: [] })
    getIssueTypesMock.mockResolvedValue({ data: [] })
    getIntakeArchiveMock.mockResolvedValue({
      data: [
        {
          id: '11111111-1111-1111-1111-111111111111',
          reason_code: 'REJECTED',
          model_id: 'LiquidAI/LFM2.5-VL-1.6B-GGUF',
          model_quantization: 'Q8_0',
          selected_category_name_snapshot: null,
          reporter_notes: 'Banner photo',
          file_path: 'issues/archive-one.jpg',
          mime_type: 'image/jpeg',
          created_at: '2026-04-13T06:00:00Z',
        },
      ],
    })
  })

  it('loads rejected submissions and shows preview details', async () => {
    render(
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Intake Archive' }))

    await waitFor(() =>
      expect(getIntakeArchiveMock).toHaveBeenCalledTimes(1)
    )

    expect(screen.getByText('Rejected Intake Archive')).toBeInTheDocument()
    expect(screen.getAllByText('REJECTED')).toHaveLength(2)
    expect(
      screen.getByRole('img', { name: 'Archived submission preview' })
    ).toHaveAttribute(
      'src',
      expect.stringContaining('/admin/intake-archive/11111111-1111-1111-1111-111111111111/image')
    )
    expect(screen.getByText('Banner photo')).toBeInTheDocument()
  })
})
