import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Important for cookies
});

// Remove request interceptor that adds header
// (Browser handles cookie automatically)

// Add response interceptor for 401 handling
let isRefreshing = false;
let failedQueue = [];

const isRefreshRequest = (request) => {
  const requestUrl = request?.url;
  return typeof requestUrl === 'string' && requestUrl.includes('/auth/refresh');
};

const shouldRedirectToLogin = () => {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.location.pathname !== '/login';
};

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401
      && !originalRequest._retry
      && !isRefreshRequest(originalRequest)
    ) {
      if (isRefreshing) {
        return new Promise(function(resolve, reject) {
          failedQueue.push({ resolve, reject });
        }).then(() => {
          return api(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await api.post('/auth/refresh');
        processQueue(null);
        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        if (shouldRedirectToLogin()) {
          window.location.href = '/login';
        }
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
export { API_URL };
