import { Routes, Route } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import Login from './pages/Login'
import CitizenHome from './pages/citizen/CitizenHome'
import ReportIssue from './pages/citizen/ReportIssue'
import MyReports from './pages/citizen/MyReports'
import AuthorityDashboard from './pages/authority/AuthorityDashboard'
import WorkerHome from './pages/worker/WorkerHome'
import AdminDashboard from './pages/admin/AdminDashboard'
import PrivateRoute from './components/PrivateRoute'
import { useOfflineSync } from './hooks/useOfflineSync'
import AnalyticsDashboard from './pages/AnalyticsDashboard'

function App() {
  useOfflineSync()
  
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        
        {/* Citizen Routes */}
        <Route path="/citizen" element={<PrivateRoute role="CITIZEN" />}>
          <Route index element={<CitizenHome />} />
          <Route path="report" element={<ReportIssue />} />
          <Route path="my-reports" element={<MyReports />} />
        </Route>

        {/* Authority Routes */}
        <Route path="/authority" element={<PrivateRoute role="ADMIN" />}>
          <Route index element={<AuthorityDashboard />} />
        </Route>

        {/* Worker Routes */}
        <Route path="/worker" element={<PrivateRoute role="WORKER" />}>
          <Route index element={<WorkerHome />} />
        </Route>

        {/* Admin Routes */}
        <Route path="/admin" element={<PrivateRoute role="SYSADMIN" />}>
          <Route index element={<AdminDashboard />} />
        </Route>

        <Route path="*" element={<Login />} />
      </Routes>
    </div>
  )
}

export default App
