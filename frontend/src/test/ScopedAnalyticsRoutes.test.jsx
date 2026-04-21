import { MemoryRouter } from 'react-router-dom'
import { act, render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AnalyticsDashboard from '../pages/AnalyticsDashboard'
import AuthorityDashboard from '../pages/authority/AuthorityDashboard'

const apiGetMock = vi.fn()
const useAutoRefreshMock = vi.fn()

vi.mock('../services/api', () => ({
  default: {
    get: (...args) => apiGetMock(...args),
  },
}))

vi.mock('../hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../hooks/useGeolocation', () => ({
  useGeolocation: () => ({
    position: null,
  }),
  DEFAULT_CENTER: { lat: 17.44, lng: 78.35 },
}))

vi.mock('../hooks/useAutoRefresh', () => ({
  useAutoRefresh: (...args) => useAutoRefreshMock(...args),
}))

vi.mock('../components/InteractiveMap', () => ({
  InteractiveMap: ({ children }) => <div data-testid="interactive-map">{children}</div>,
  Marker: () => <div data-testid="interactive-marker" />,
  Popup: ({ children }) => <div>{children}</div>,
}))

vi.mock('../components/MapboxHeatmap', () => ({
  MapboxHeatmap: () => <div data-testid="heatmap" />,
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  PieChart: () => <div />,
  Pie: () => <div />,
  Cell: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  AreaChart: () => <div />,
  Area: () => null,
}))

vi.mock('../features/common/components/SidebarItem', () => ({
  SidebarItem: ({ label, onClick }) => <button onClick={onClick}>{label}</button>,
}))

vi.mock('../features/common/components/StatCard', () => ({
  StatCard: ({ label, value }) => <div>{label}:{value}</div>,
}))

vi.mock('../features/authority/components/IssueKanban/Card', () => ({
  KanbanCard: () => <div>card</div>,
}))

vi.mock('../features/authority/components/IssueKanban/Column', () => ({
  KanbanColumn: ({ children }) => <div>{children}</div>,
}))

vi.mock('../features/authority/components/IssueKanban/ActionsDropdown', () => ({
  IssueActionsDropdown: () => <div>actions</div>,
}))

vi.mock('../features/authority/components/Modals/IssueReviewModal', () => ({
  IssueReviewModal: () => null,
}))

vi.mock('../features/authority/components/WorkerAnalytics/WorkersTable', () => ({
  WorkersTable: () => <div>workers</div>,
}))

vi.mock('../features/authority/components/WorkerAnalytics/AnalyticsPanel', () => ({
  AnalyticsPanel: () => <div>analytics-panel</div>,
}))

vi.mock('../features/authority/components/Modals/OnboardWorkersModal', () => ({
  OnboardWorkersModal: () => null,
}))

vi.mock('../services/admin', () => ({
  default: {
    assignIssueCategory: vi.fn(),
  },
}))

vi.mock('../services/auth', () => ({
  authService: {
    logout: vi.fn(),
  },
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

describe('scoped analytics routes', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    const { useAuth } = await import('../hooks/useAuth')
    useAuth.mockReturnValue({
      user: { role: 'ADMIN' },
    })
  })

  it('uses admin-scoped analytics endpoints for admin users on the analytics page', async () => {
    apiGetMock.mockImplementation((url) => {
      if (url === '/admin/stats') {
        return Promise.resolve({
          data: {
            summary: { reported: 1, workers: 1, resolved: 0, compliance: '0.0%' },
            category_split: [],
            status_split: [],
            trend: [],
          },
        })
      }
      if (url === '/admin/heatmap') {
        return Promise.resolve({ data: [] })
      }
      if (url === '/admin/issues-map') {
        return Promise.resolve({ data: [] })
      }
      throw new Error(`Unexpected GET ${url}`)
    })

    render(
      <MemoryRouter>
        <AnalyticsDashboard />
      </MemoryRouter>
    )

    await waitFor(() =>
      expect(apiGetMock).toHaveBeenCalledWith('/admin/stats')
    )
    expect(apiGetMock).toHaveBeenCalledWith('/admin/heatmap')
    expect(apiGetMock).toHaveBeenCalledWith('/admin/issues-map')
  })

  it('uses admin-scoped heatmap data on the authority operations map', async () => {
    apiGetMock.mockImplementation((url) => {
      if (url === '/admin/issues') {
        return Promise.resolve({ data: [] })
      }
      if (url === '/admin/workers-with-stats') {
        return Promise.resolve({ data: [] })
      }
      if (url === '/admin/heatmap') {
        return Promise.resolve({ data: [] })
      }
      if (url === '/admin/worker-analytics') {
        return Promise.resolve({ data: { workers: [], summary: {} } })
      }
      if (url === '/categories') {
        return Promise.resolve({ data: [] })
      }
      throw new Error(`Unexpected GET ${url}`)
    })

    render(
      <MemoryRouter>
        <AuthorityDashboard />
      </MemoryRouter>
    )

    const refreshCallback = useAutoRefreshMock.mock.calls[0][0]
    await act(async () => {
      await refreshCallback()
    })

    await waitFor(() =>
      expect(apiGetMock).toHaveBeenCalledWith('/admin/heatmap')
    )
    expect(apiGetMock).not.toHaveBeenCalledWith('/analytics/heatmap')
  })
})
