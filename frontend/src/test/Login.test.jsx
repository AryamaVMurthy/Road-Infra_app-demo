import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Login from '../pages/Login'
import { BrowserRouter } from 'react-router-dom'

// Mock auth service
vi.mock('../services/auth', () => ({
  authService: {
    requestOtp: vi.fn().mockResolvedValue({}),
    login: vi.fn().mockResolvedValue({ access_token: 'fake-token' }),
    getCurrentUser: vi.fn().mockReturnValue({ role: 'CITIZEN', sub: 'test@example.com' })
  }
}))

describe('Login Component', () => {
  it('renders email input initially', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    expect(screen.getByPlaceholderText(/ghmc.gov.in/i)).toBeDefined()
    expect(screen.getByText(/Request Access/i)).toBeDefined()
  })

  it('switches to OTP step after email submission', async () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    
    const emailInput = screen.getByPlaceholderText(/ghmc.gov.in/i)
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    
    const requestBtn = screen.getByText(/Request Access/i)
    fireEvent.click(requestBtn)
    
    // Wait for the text to appear
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Enter 6-digit code/i)).toBeDefined()
    })
  })
})
