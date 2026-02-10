import api from './api'

const isUnauthorized = (error) => error?.response?.status === 401

export const authService = {
  requestOtp: async (email) => {
    return api.post('/auth/otp-request', { email })
  },
  login: async (email, otp) => {
    // No response data usage (tokens are cookies)
    const response = await api.post('/auth/login', { email, otp })
    return response.data
  },
  logout: async () => {
    await api.post('/auth/logout')
    window.location.href = '/login'
  },
  getCurrentUser: async () => {
    try {
      const response = await api.get('/auth/me')
      return response.data
    } catch (error) {
      if (isUnauthorized(error)) {
        return null
      }
      throw error
    }
  }
}
