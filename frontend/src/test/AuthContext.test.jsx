import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider, useAuth } from '../hooks/useAuth';
import { render, screen, waitFor, act } from '@testing-library/react';
import { authService } from '../services/auth';

vi.mock('../services/auth', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    requestOtp: vi.fn()
  }
}));

const TestComponent = () => {
  const { user, loading, logout } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!user) return <div>Guest</div>;
  return (
    <div>
      <span>{user.email}</span>
      <button onClick={() => logout()}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with guest state if no user found', async () => {
    authService.getCurrentUser.mockResolvedValue(null);
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeDefined();
    await waitFor(() => expect(screen.getByText('Guest')).toBeDefined());
  });

  it('should hydrate user state on mount', async () => {
    const mockUser = { email: 'hydrated@test.com', role: 'CITIZEN' };
    authService.getCurrentUser.mockResolvedValue(mockUser);
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByText('hydrated@test.com')).toBeDefined());
  });

  it('should retry hydration on transient error before logging out', async () => {
    const mockUser = { email: 'retry@test.com', role: 'ADMIN' };
    authService.getCurrentUser.mockRejectedValueOnce(new Error('Network Error'));
    authService.getCurrentUser.mockResolvedValueOnce(mockUser);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(
      () => expect(screen.getByText('retry@test.com')).toBeDefined(),
      { timeout: 3000 }
    );

    expect(authService.getCurrentUser).toHaveBeenCalledTimes(2);
  });

  it('should update state after successful login', async () => {
    authService.getCurrentUser.mockResolvedValueOnce(null);
    const mockUser = { email: 'loggedin@test.com', role: 'ADMIN' };
    authService.login.mockResolvedValue({ message: 'Success' });
    authService.getCurrentUser.mockResolvedValueOnce(mockUser);

    let auth;
    const GrabAuth = () => {
        auth = useAuth();
        return null;
    };

    render(
      <AuthProvider>
        <GrabAuth />
      </AuthProvider>
    );

    await waitFor(() => expect(auth.loading).toBe(false));
    
    await act(async () => {
        await auth.login('test@test.com', '123456');
    });

    expect(auth.user).toEqual(mockUser);
  });
});
