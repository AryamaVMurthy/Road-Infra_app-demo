import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const authService = {
  requestOtp: async (email) => {
    return axios.post(`${API_URL}/auth/otp-request`, { email })
  },
  login: async (email, otp) => {
    const response = await axios.post(`${API_URL}/auth/login`, { email, otp })
    if (response.data.access_token) {
      localStorage.setItem('user', JSON.stringify(response.data))
    }
    return response.data
  },
  logout: () => {
    localStorage.removeItem('user')
    window.location.href = '/login'
  },
  getCurrentUser: () => {
    const user = localStorage.getItem('user')
    if (user) {
      const decoded = JSON.parse(atob(JSON.parse(user).access_token.split('.')[1]))
      return decoded
    }
    return null
  }
}
