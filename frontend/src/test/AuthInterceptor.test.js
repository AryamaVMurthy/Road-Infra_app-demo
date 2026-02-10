import { describe, it, expect, vi, beforeEach } from 'vitest';

const { createMockInstance } = vi.hoisted(() => {
  return {
    createMockInstance: () => {
      const mock = vi.fn();
      mock.interceptors = {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() }
      };
      mock.post = vi.fn();
      mock.get = vi.fn();
      mock.defaults = { headers: { common: {} } };
      return mock;
    }
  };
});

let currentMock;

vi.mock('axios', () => {
  return {
    default: {
      create: vi.fn(() => currentMock)
    }
  };
});

describe('Auth Interceptor', () => {
  beforeEach(async () => {
    currentMock = createMockInstance();
    vi.clearAllMocks();
    vi.resetModules();
  });

  it('should attempt refresh on 401 error', async () => {
    await import('../services/api');
    
    const responseInterceptorFail = currentMock.interceptors.response.use.mock.calls[0][1];
    
    const originalRequest = { url: '/test', _retry: false };
    const error = {
      response: { status: 401 },
      config: originalRequest
    };

    currentMock.post.mockResolvedValueOnce({ status: 200 }); 
    
    await responseInterceptorFail(error);

    expect(currentMock.post).toHaveBeenCalledWith('/auth/refresh');
    expect(originalRequest._retry).toBe(true);
  });

  it('should redirect to login if refresh fails', async () => {
    await import('../services/api');
    
    const responseInterceptorFail = currentMock.interceptors.response.use.mock.calls[0][1];
    
    const originalRequest = { url: '/test', _retry: false };
    const error = {
      response: { status: 401 },
      config: originalRequest
    };

    currentMock.post.mockRejectedValueOnce({ response: { status: 401 } }); 
    
    const originalLocation = window.location;
    delete window.location;
    window.location = { href: '' };

    try {
      await responseInterceptorFail(error);
    } catch (e) {
    }

    expect(window.location.href).toBe('/login');
    window.location = originalLocation;
  });

  it('should not try to refresh when refresh endpoint returns 401', async () => {
    await import('../services/api');

    const responseInterceptorFail = currentMock.interceptors.response.use.mock.calls[0][1];

    const refreshRequest = { url: '/auth/refresh', _retry: false };
    const error = {
      response: { status: 401 },
      config: refreshRequest
    };

    await expect(responseInterceptorFail(error)).rejects.toBe(error);
    expect(currentMock.post).not.toHaveBeenCalled();
    expect(refreshRequest._retry).toBe(false);
  });

  it('should not force reload when already on login route', async () => {
    await import('../services/api');

    const responseInterceptorFail = currentMock.interceptors.response.use.mock.calls[0][1];

    const originalRequest = { url: '/auth/me', _retry: false };
    const error = {
      response: { status: 401 },
      config: originalRequest
    };

    const refreshError = { response: { status: 401 } };
    currentMock.post.mockRejectedValueOnce(refreshError);

    const originalLocation = window.location;
    delete window.location;
    window.location = { href: '/login', pathname: '/login' };

    await expect(responseInterceptorFail(error)).rejects.toBe(refreshError);
    expect(window.location.href).toBe('/login');

    window.location = originalLocation;
  });

  it('should not redirect to login when refresh fails with server error', async () => {
    await import('../services/api');

    const responseInterceptorFail = currentMock.interceptors.response.use.mock.calls[0][1];

    const originalRequest = { url: '/auth/me', _retry: false };
    const error = {
      response: { status: 401 },
      config: originalRequest
    };

    const refreshError = { response: { status: 500 } };
    currentMock.post.mockRejectedValueOnce(refreshError);

    const originalLocation = window.location;
    delete window.location;
    window.location = { href: '/authority', pathname: '/authority' };

    await expect(responseInterceptorFail(error)).rejects.toBe(refreshError);
    expect(window.location.href).toBe('/authority');

    window.location = originalLocation;
  });
});
