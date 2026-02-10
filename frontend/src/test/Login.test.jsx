import { act, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Login from '../pages/Login'
import { BrowserRouter } from 'react-router-dom'

// Mock auth service
vi.mock('../services/auth', () => ({
  authService: {
    requestOtp: vi.fn().mockResolvedValue({}),
    login: vi.fn().mockResolvedValue({ access_token: 'fake-token' }),
    getCurrentUser: vi.fn().mockResolvedValue(null)
  }
}))

import { AuthProvider } from '../hooks/useAuth'
import { authService } from '../services/auth'

const ROUTER_FUTURE_FLAGS = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
}

const renderLogin = async () => {
  await act(async () => {
    render(
      <BrowserRouter future={ROUTER_FUTURE_FLAGS}>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </BrowserRouter>
    )
  })
  await waitFor(() => {
    expect(authService.getCurrentUser).toHaveBeenCalled()
  })
}

describe('Login Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authService.getCurrentUser.mockResolvedValue(null)
  })

  it('renders email input initially', async () => {
    await renderLogin()
    expect(screen.getByPlaceholderText(/authority.gov.in/i)).toBeDefined()
    expect(screen.getByText(/Request Access/i)).toBeDefined()
  })

  it('switches to OTP step after email submission', async () => {
    await renderLogin()
    
    const emailInput = screen.getByPlaceholderText(/authority.gov.in/i)
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    
    const requestBtn = screen.getByText(/Request Access/i)
    fireEvent.click(requestBtn)
    
    // Wait for the text to appear
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Enter 6-digit code/i)).toBeDefined()
    })
  })
})
