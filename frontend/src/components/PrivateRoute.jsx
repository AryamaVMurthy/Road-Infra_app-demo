import { Navigate, Outlet } from 'react-router-dom'
import { authService } from '../services/auth'

export default function PrivateRoute({ role }) {
  const user = authService.getCurrentUser()
  
  if (!user) {
    return <Navigate to="/login" />
  }
  
  if (role && user.role !== role) {
    return <Navigate to="/login" />
  }
  
  return <Outlet />
}
