import { useState, useEffect, useCallback } from 'react'
import api, { API_URL } from '../../services/api'
import { 
    LayoutDashboard, Map as MapIcon, Users, LogOut, 
    CheckCircle2, AlertCircle, Clock,
    CheckSquare, Globe, RefreshCw, XCircle, UserPlus, MailPlus, Menu, X
} from 'lucide-react'
import { authService } from '../../services/auth'
import adminService from '../../services/admin'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'

import { InteractiveMap } from '../../components/InteractiveMap'
import { IssueMarkersLayer } from '../../components/IssueMarkersLayer'
import { MapboxHeatmap } from '../../components/MapboxHeatmap'
import { useGeolocation, DEFAULT_CENTER } from '../../hooks/useGeolocation'

import { SidebarItem } from '../../features/common/components/SidebarItem'
import { StatCard } from '../../features/common/components/StatCard'
import { KanbanCard } from '../../features/authority/components/IssueKanban/Card'
import { KanbanColumn } from '../../features/authority/components/IssueKanban/Column'
import { IssueActionsDropdown } from '../../features/authority/components/IssueKanban/ActionsDropdown'
import { IssueReviewModal } from '../../features/authority/components/Modals/IssueReviewModal'
import { WorkersTable } from '../../features/authority/components/WorkerAnalytics/WorkersTable'
import { AnalyticsPanel } from '../../features/authority/components/WorkerAnalytics/AnalyticsPanel'
import { OnboardWorkersModal } from '../../features/authority/components/Modals/OnboardWorkersModal'

export default function AuthorityDashboard() {
  const [activeTab, setActiveTab] = useState('map') 
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024)
  const [issues, setIssues] = useState([])

  useEffect(() => {
    const handleResize = () => setIsDesktop(window.innerWidth >= 1024)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  const [workers, setWorkers] = useState([])
  const [workerAnalytics, setWorkerAnalytics] = useState(null)
  
  const [selectedIssues, setSelectedIssues] = useState([])
  const [reviewIssue, setReviewIssue] = useState(null)
  const [mapMode, setMapMode] = useState('markers')
  const [heatmapData, setHeatmapData] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [showOnboardModal, setShowOnboardModal] = useState(false)
  const navigate = useNavigate()
  
  const { position: geoPosition } = useGeolocation()
  const userLocation = geoPosition ? [geoPosition.lat, geoPosition.lng] : [DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]

  const fetchData = useCallback(() => {
    Promise.all([
      api.get('/admin/issues'), 
      api.get('/admin/workers-with-stats'),
      api.get('/analytics/heatmap'),
      api.get('/admin/worker-analytics')
    ]).then(([issuesRes, workersRes, heatRes, analyticsRes]) => {
        setIssues(issuesRes.data)
        setWorkers(workersRes.data)
        setHeatmapData(heatRes.data)
        setWorkerAnalytics(analyticsRes.data)
      }).catch(err => console.error('Fetch failed:', err))
  }, [])

  useEffect(() => { 
    fetchData()
    
    const interval = setInterval(() => {
        fetchData()
        setLastRefresh(new Date())
    }, 30000)
    
    return () => clearInterval(interval)
  }, [fetchData])

  const toggleIssueSelection = (id) => {
    setSelectedIssues(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id])
  }

  const handleBulkAssign = async (workerId) => {
    if (selectedIssues.length === 0) return
    try {
      await api.post('/admin/bulk-assign', { issue_ids: selectedIssues, worker_id: workerId })
      setSelectedIssues([]); fetchData()
    } catch (err) { alert('Assignment failed') }
  }

  const handleApprove = async (id) => {
    setSubmitting(true)
    try {
        await api.post(`/admin/approve?issue_id=${id}`)
        setReviewIssue(null)
        fetchData()
    } catch (e) { alert("Approval failed") }
    setSubmitting(false)
  }

  const handleReject = async (id, reason) => {
    if (!reason) return alert("Please provide a reason")
    setSubmitting(true)
    try {
        await api.post(`/admin/reject?issue_id=${id}&reason=${reason}`)
        setReviewIssue(null)
        fetchData()
    } catch (e) { alert("Rejection failed") }
    setSubmitting(false)
  }

  const handleOnboard = async (emails) => {
    setSubmitting(true)
    try {
        await adminService.bulkInviteWorkers(emails)
        setShowOnboardModal(false)
        fetchData()
    } catch (e) { alert("Onboarding failed") }
    setSubmitting(false)
  }

  const handleActivateWorker = async (workerId) => {
    try {
      await api.post(`/admin/activate-worker?worker_id=${workerId}`)
      fetchData()
    } catch (e) {
      alert('Failed to activate worker')
    }
  }

  const handleDeactivateWorker = async (workerId) => {
    if (!window.confirm("Are you sure you want to deactivate this worker?")) return
    try {
        await api.post(`/admin/deactivate-worker?worker_id=${workerId}`)
        fetchData()
    } catch (e) { alert("Deactivation failed") }
  }

  const reportedCount = issues.filter(i => i.status === 'REPORTED').length
  const inFieldCount = issues.filter(i => ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'].includes(i.status)).length
  const resolvedCount = issues.filter(i => i.status === 'RESOLVED' || i.status === 'CLOSED').length

  return (
    <div className="flex h-screen bg-[#F8FAFC] relative overflow-hidden">
      <AnimatePresence>
        {(isSidebarOpen || isDesktop) && (
          <motion.aside 
            initial={isDesktop ? false : { x: -288 }}
            animate={{ x: 0 }}
            exit={{ x: -288 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className={cn(
              "w-72 bg-white border-r border-slate-100 flex flex-col p-6 fixed lg:relative z-[100] h-full shadow-2xl lg:shadow-none",
              !isSidebarOpen && !isDesktop && "hidden"
            )}
          >
            <div className="flex items-center justify-between mb-12">
                <div className="flex items-center gap-4 px-2">
                    <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center text-white shadow-lg">
                        <LayoutDashboard size={24} />
                    </div>
                    <div>
                        <h1 className="text-lg font-black tracking-tight text-slate-900 leading-none">MARG</h1>
                    </div>
                </div>
                <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden text-slate-400 hover:text-slate-900">
                    <X size={24} />
                </button>
            </div>

            <nav className="flex-1 space-y-2">
              <SidebarItem active={activeTab === 'map'} icon={MapIcon} label="Operations Map" onClick={() => setActiveTab('map')} />
              <SidebarItem active={activeTab === 'kanban'} icon={CheckSquare} label="Kanban Triage" onClick={() => setActiveTab('kanban')} />
              <SidebarItem active={activeTab === 'workers'} icon={Users} label="Field Force" onClick={() => setActiveTab('workers')} />
              <SidebarItem active={false} icon={Globe} label="City Analytics" onClick={() => navigate('/analytics')} />
            </nav>

            <div className="mt-auto space-y-4">
                <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-xl text-xs text-slate-500">
                    <RefreshCw size={12} className="animate-spin-slow" />
                    <span>Auto-refresh: {lastRefresh.toLocaleTimeString()}</span>
                </div>
                <button onClick={() => authService.logout()} className="w-full flex items-center gap-4 p-4 text-red-500 font-bold hover:bg-red-50 rounded-2xl transition-colors">
                    <LogOut size={20} /> <span className="text-sm">Log Out</span>
                </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-20 lg:h-24 px-6 lg:px-10 flex items-center justify-between border-b border-slate-100 bg-white/50 backdrop-blur-md">
            <div className="flex items-center gap-4 lg:gap-6">
                <button 
                    onClick={() => setIsSidebarOpen(true)}
                    className="lg:hidden w-10 h-10 bg-white border border-slate-100 rounded-xl flex items-center justify-center text-slate-600 shadow-sm"
                >
                    <Menu size={20} />
                </button>
                <h2 className="text-xl lg:text-2xl font-black text-slate-900 capitalize truncate">{activeTab}</h2>
                {activeTab === 'workers' && (
                    <button 
                        onClick={() => setShowOnboardModal(true)}
                        className="bg-primary text-white px-4 py-2 rounded-xl text-xs font-black shadow-lg shadow-primary/20 flex items-center gap-2 hover:bg-primary/90 transition-all active:scale-95"
                    >
                        <UserPlus size={14} />
                        Onboard
                    </button>
                )}
            </div>
            <div className="flex items-center gap-4">
                <button onClick={fetchData} className="p-2 bg-slate-100 rounded-xl text-slate-500 hover:text-primary hover:bg-primary/10 transition-all">
                    <RefreshCw size={18} />
                </button>
                <div className="text-right">
                    <p className="text-sm font-bold text-slate-900">Admin</p>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Live Session</p>
                </div>
                <div className="w-12 h-12 bg-slate-100 rounded-2xl border-2 border-white shadow-md flex items-center justify-center text-primary font-black">AD</div>
            </div>
        </header>

        <main className="flex-1 overflow-auto p-10">
           <AnimatePresence mode="wait">
            {activeTab === 'map' && (
                <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="h-full space-y-8 flex flex-col">
                    <div className="flex items-center justify-between">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 flex-1 mr-8">
                            <StatCard label="Reported" value={reportedCount} icon={AlertCircle} colorClass="bg-rose-500 shadow-rose-200/50" />
                            <StatCard label="In Field" value={inFieldCount} icon={Users} colorClass="bg-blue-500 shadow-blue-200/50" />
                            <StatCard label="Resolved" value={resolvedCount} icon={CheckCircle2} colorClass="bg-emerald-500 shadow-emerald-200/50" />
                        </div>
                        <div className="flex bg-white p-1 rounded-2xl border shadow-sm h-fit">
                            <button onClick={() => setMapMode('markers')} className={cn("px-4 py-2 rounded-xl text-xs font-black transition-all", mapMode === 'markers' ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-slate-400 hover:text-slate-900")}>Markers</button>
                            <button onClick={() => setMapMode('heatmap')} className={cn("px-4 py-2 rounded-xl text-xs font-black transition-all", mapMode === 'heatmap' ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-slate-400 hover:text-slate-900")}>Heatmap</button>
                        </div>
                    </div>
                    <div className="flex-1 rounded-[3rem] overflow-hidden border-8 border-white shadow-2xl relative">
                        <InteractiveMap
                            initialViewState={{
                                longitude: userLocation[1],
                                latitude: userLocation[0],
                                zoom: 14
                            }}
                        >
                            {mapMode === 'markers' ? (
                                <IssueMarkersLayer
                                    issues={issues}
                                    renderPopupContent={(issue) => (
                                        <div className="p-3 w-64 space-y-3">
                                            <div className="flex justify-between items-start">
                                                <p className="font-black text-slate-900">{issue.category_name}</p>
                                                <span className="text-[9px] font-black uppercase text-primary px-1.5 py-0.5 bg-primary/5 rounded">{issue.status}</span>
                                            </div>
                                            <div className="text-[10px] text-slate-500 space-y-1">
                                                <div className="flex items-center gap-1">
                                                    <Clock size={10} />
                                                    Registered: {new Date(issue.created_at).toLocaleDateString()}
                                                </div>
                                                {issue.eta_date && (
                                                    <div className="flex items-center gap-1 text-amber-600 font-bold">
                                                        <Clock size={10} />
                                                        ETA: {new Date(issue.eta_date).toLocaleDateString()}
                                                    </div>
                                                )}
                                                {issue.accepted_at && (
                                                    <div className="flex items-center gap-1">
                                                        Accepted: {new Date(issue.accepted_at).toLocaleDateString()}
                                                    </div>
                                                )}
                                                {issue.resolved_at && (
                                                    <div className="flex items-center gap-1 text-emerald-600 font-bold">
                                                        Resolved: {new Date(issue.resolved_at).toLocaleDateString()}
                                                    </div>
                                                )}
                                            </div>
                                            <div className="aspect-video bg-slate-100 rounded-lg overflow-hidden border">
                                                <img src={`${API_URL}/media/${issue.id}/before`} className="w-full h-full object-cover" alt="Issue" />
                                            </div>
                                            <button onClick={() => setReviewIssue(issue)} className="w-full py-2 bg-primary text-white rounded-lg text-[10px] font-bold">Open Operations Console</button>
                                        </div>
                                    )}
                                />
                            ) : ( <MapboxHeatmap points={heatmapData} /> )}
                        </InteractiveMap>
                    </div>
                </motion.div>
            )}

            {activeTab === 'kanban' && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col h-full gap-8">
                    <AnalyticsPanel analytics={workerAnalytics} />
                    
                    {selectedIssues.length > 0 && (
                        <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} className="flex items-center gap-4 px-6 py-2 bg-primary rounded-2xl shadow-xl shadow-primary/30">
                            <span className="text-sm font-black text-white">{selectedIssues.length} SELECTED</span>
                            <select 
                                className="bg-white/10 text-white border-none rounded-lg text-xs font-bold py-1.5 focus:ring-0 outline-none"
                                onChange={(e) => handleBulkAssign(e.target.value)} value=""
                            >
                                <option value="" className="text-black">Bulk Assign to...</option>
                                {workers.map(w => (
                                    <option key={w.id} value={w.id} className="text-black">
                                        {w.full_name} ({w.active_task_count} tasks)
                                    </option>
                                ))}
                            </select>
                            <button onClick={() => setSelectedIssues([])} className="text-white/60 hover:text-white transition-colors"><XCircle size={18}/></button>
                        </motion.div>
                    )}
                    
                    <div className="flex gap-8 overflow-x-auto pb-6 h-full">
                        {[
                            { key: 'REPORTED', label: 'REPORTED', statuses: ['REPORTED'], color: 'rose' },
                            { key: 'ASSIGNED', label: 'ASSIGNED', statuses: ['ASSIGNED', 'ACCEPTED'], color: 'blue' },
                            { key: 'IN_PROGRESS', label: 'IN PROGRESS', statuses: ['IN_PROGRESS'], color: 'amber' },
                            { key: 'RESOLVED', label: 'RESOLVED', statuses: ['RESOLVED'], color: 'emerald' },
                            { key: 'CLOSED', label: 'CLOSED', statuses: ['CLOSED'], color: 'slate' },
                        ].map(column => (
                            <KanbanColumn 
                                key={column.key} 
                                title={column.label} 
                                color={column.color} 
                                count={issues.filter(i => column.statuses.includes(i.status)).length}
                            >
                                {issues.filter(i => column.statuses.includes(i.status)).map(issue => (
                                    <KanbanCard 
                                        key={issue.id} 
                                        issue={issue}
                                        selected={selectedIssues.includes(issue.id)}
                                        onClick={() => setReviewIssue(issue)}
                                        onSelectToggle={toggleIssueSelection}
                                        showCheckbox={column.key === 'REPORTED'}
                                        actions={
                                            <IssueActionsDropdown 
                                                issue={issue} 
                                                workers={workers}
                                                onUpdate={fetchData}
                                                api={api}
                                            />
                                        }
                                    />
                                ))}
                            </KanbanColumn>
                        ))}
                    </div>
                </motion.div>
            )}

            {activeTab === 'workers' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                    <div className="flex justify-between items-center">
                        <AnalyticsPanel analytics={workerAnalytics} />
                        <button 
                            onClick={() => setShowOnboardModal(true)}
                            className="bg-primary text-white px-6 py-4 rounded-2xl font-black shadow-xl shadow-primary/20 flex items-center gap-2 hover:bg-primary/90 transition-all active:scale-95"
                        >
                            <UserPlus size={20} />
                            Onboard Workers
                        </button>
                    </div>
                    <WorkersTable 
                        workers={workers} 
                        analytics={workerAnalytics} 
                        onActivate={handleActivateWorker}
                        onDeactivate={handleDeactivateWorker}
                    />
                </motion.div>
            )}
           </AnimatePresence>

           <IssueReviewModal 
                issue={reviewIssue}
                onClose={() => setReviewIssue(null)}
                onApprove={handleApprove}
                onReject={handleReject}
                submitting={submitting}
           />

           {showOnboardModal && (
               <OnboardWorkersModal 
                    onOnboard={handleOnboard}
                    onCancel={() => setShowOnboardModal(false)}
                    isSubmitting={submitting}
               />
           )}
        </main>
      </div>
    </div>
  )
}
