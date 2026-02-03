import React, { useState, useEffect, useRef } from 'react'
import api, { API_URL } from '../../services/api'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { 
    LayoutDashboard, Map as MapIcon, Users, LogOut, Filter, 
    ChevronDown, CheckCircle2, AlertCircle, Clock,
    CheckSquare, XCircle, Camera, Info, X, MapPin, ChevronRight, Activity, Globe,
    UserPlus, TrendingUp, Zap, Award, BarChart3, RefreshCw
} from 'lucide-react'
import { authService } from '../../services/auth'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'

import { HeatmapLayer } from '../../components/HeatmapLayer'
import { LocateControl } from '../../components/LocateControl'
import { SearchField } from '../../components/SearchField'
import { useGeolocation, HYDERABAD_CENTER } from '../../hooks/useGeolocation'

const MAP_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

const SidebarItem = ({ active, icon: Icon, label, onClick }) => (
    <button 
        onClick={onClick}
        className={cn(
            "w-full flex items-center gap-4 p-4 rounded-2xl font-bold transition-all group",
            active ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
        )}
    >
        <Icon size={22} className={cn("transition-transform group-hover:scale-110", active ? "text-white" : "text-slate-400")} />
        <span className="text-sm">{label}</span>
    </button>
)

const StatCard = ({ label, value, icon: Icon, colorClass, trend }) => (
    <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 flex items-center gap-6">
        <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center text-white", colorClass)}>
            <Icon size={24} />
        </div>
        <div className="flex-1">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">{label}</p>
            <p className="text-3xl font-extrabold text-slate-900">{value}</p>
        </div>
        {trend && (
            <div className="flex items-center gap-1 text-emerald-500 text-xs font-bold">
                <TrendingUp size={14} />
                {trend}
            </div>
        )}
    </div>
)

// Quick Assign Dropdown Component
const QuickAssignDropdown = ({ issue, workers, onAssign }) => {
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const dropdownRef = useRef(null)

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleAssign = async (workerId) => {
        setLoading(true)
        try {
            await api.post(`/admin/assign?issue_id=${issue.id}&worker_id=${workerId}`)
            setIsOpen(false)
            onAssign()
        } catch (err) {
            alert('Assignment failed')
        }
        setLoading(false)
    }

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen) }}
                className="flex items-center gap-1 px-3 py-1.5 bg-primary/10 text-primary rounded-full text-[10px] font-black uppercase tracking-tight hover:bg-primary hover:text-white transition-all"
            >
                <UserPlus size={12} />
                Assign
            </button>
            
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: -10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -10, scale: 0.95 }}
                        className="absolute top-full right-0 mt-2 w-64 bg-white rounded-2xl shadow-2xl border border-slate-100 z-50 overflow-hidden"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="p-3 border-b border-slate-100 bg-slate-50">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Assign to Worker</p>
                        </div>
                        <div className="max-h-64 overflow-y-auto">
                            {workers.map(worker => (
                                <button
                                    key={worker.id}
                                    onClick={() => handleAssign(worker.id)}
                                    disabled={loading}
                                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors disabled:opacity-50"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center text-primary font-black text-xs">
                                            {worker.full_name?.[0] || 'W'}
                                        </div>
                                        <div className="text-left">
                                            <p className="text-sm font-bold text-slate-900">{worker.full_name || worker.email}</p>
                                            <p className="text-[10px] text-slate-400">{worker.email}</p>
                                        </div>
                                    </div>
                                    <div className={cn(
                                        "px-2 py-1 rounded-full text-[10px] font-black",
                                        worker.active_task_count === 0 ? "bg-emerald-50 text-emerald-600" :
                                        worker.active_task_count <= 2 ? "bg-blue-50 text-blue-600" :
                                        "bg-amber-50 text-amber-600"
                                    )}>
                                        {worker.active_task_count} tasks
                                    </div>
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

// Worker Analytics Mini Card
const WorkerAnalyticsMini = ({ analytics }) => {
    if (!analytics) return null
    
    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-[2.5rem] p-8 text-white mb-8"
        >
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center">
                        <BarChart3 size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-black">Workforce Overview</h3>
                        <p className="text-xs text-slate-400 uppercase tracking-widest">Real-time Status</p>
                    </div>
                </div>
            </div>
            
            <div className="grid grid-cols-4 gap-4">
                <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <p className="text-2xl font-black text-emerald-400">{analytics.summary?.total_workers || 0}</p>
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Total Workers</p>
                </div>
                <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <p className="text-2xl font-black text-amber-400">{analytics.summary?.total_active_tasks || 0}</p>
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Active Tasks</p>
                </div>
                <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <p className="text-2xl font-black text-blue-400">{analytics.summary?.total_resolved || 0}</p>
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Resolved</p>
                </div>
                <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                    <p className="text-2xl font-black text-purple-400">{analytics.summary?.avg_tasks_per_worker || 0}</p>
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Avg/Worker</p>
                </div>
            </div>
            
            {/* Top Performers */}
            {analytics.workers && analytics.workers.length > 0 && (
                <div className="mt-6 pt-6 border-t border-white/10">
                    <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Award size={14} className="text-amber-400" />
                        Top Performers This Week
                    </p>
                    <div className="flex gap-3">
                        {analytics.workers.slice(0, 3).map((worker, idx) => (
                            <div key={worker.worker_id} className="flex-1 bg-white/5 rounded-xl p-3 border border-white/5">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className={cn(
                                        "w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-black",
                                        idx === 0 ? "bg-amber-500 text-amber-900" :
                                        idx === 1 ? "bg-slate-400 text-slate-900" :
                                        "bg-amber-700 text-amber-200"
                                    )}>
                                        {idx + 1}
                                    </div>
                                    <p className="text-sm font-bold truncate">{worker.worker_name}</p>
                                </div>
                                <p className="text-lg font-black text-emerald-400">{worker.tasks_this_week}</p>
                                <p className="text-[9px] text-slate-500 uppercase">resolved this week</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </motion.div>
    )
}

export default function AuthorityDashboard() {
  const [activeTab, setActiveTab] = useState('map') 
  const [issues, setIssues] = useState([])
  const [workers, setWorkers] = useState([])
  const [workerAnalytics, setWorkerAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedIssues, setSelectedIssues] = useState([])
  const [reviewIssue, setReviewIssue] = useState(null)
  const [mapMode, setMapMode] = useState('markers')
  const [heatmapData, setHeatmapData] = useState([])
  const [rejectReason, setRejectReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const navigate = useNavigate()
  
  const { position: geoPosition } = useGeolocation()
  const userLocation = geoPosition ? [geoPosition.lat, geoPosition.lng] : [HYDERABAD_CENTER.lat, HYDERABAD_CENTER.lng]

  useEffect(() => { 
    fetchData()
    
    const interval = setInterval(() => {
        fetchData()
        setLastRefresh(new Date())
    }, 30000)
    
    return () => clearInterval(interval)
  }, [])

  const fetchData = () => {
    setLoading(true)
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
      .finally(() => setLoading(false))
  }

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

  const handleReject = async (id) => {
    if (!rejectReason) return alert("Please provide a reason")
    setSubmitting(true)
    try {
        await api.post(`/admin/reject?issue_id=${id}&reason=${rejectReason}`)
        setReviewIssue(null)
        setRejectReason('')
        fetchData()
    } catch (e) { alert("Rejection failed") }
    setSubmitting(false)
  }

  // Calculate stats
  const reportedCount = issues.filter(i => i.status === 'REPORTED').length
  const inFieldCount = issues.filter(i => ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'].includes(i.status)).length
  const resolvedCount = issues.filter(i => i.status === 'RESOLVED' || i.status === 'CLOSED').length

  return (
    <div className="flex h-screen bg-[#F8FAFC]">
      <aside className="w-72 bg-white border-r border-slate-100 flex flex-col p-6">
        <div className="flex items-center gap-4 px-2 mb-12">
          <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center text-white shadow-lg">
             <LayoutDashboard size={24} />
          </div>
          <div>
             <h1 className="text-lg font-black tracking-tight text-slate-900 leading-none">Authority</h1>
             <p className="text-[10px] font-bold text-primary tracking-widest uppercase mt-1">Gachibowli Admin</p>
          </div>
        </div>

        <nav className="flex-1 space-y-2">
          <SidebarItem active={activeTab === 'map'} icon={MapIcon} label="Operations Map" onClick={() => setActiveTab('map')} />
          <SidebarItem active={activeTab === 'kanban'} icon={CheckSquare} label="Kanban Triage" onClick={() => setActiveTab('kanban')} />
          <SidebarItem active={activeTab === 'workers'} icon={Users} label="Field Force" onClick={() => setActiveTab('workers')} />
          <SidebarItem active={false} icon={Globe} label="City Analytics" onClick={() => navigate('/analytics')} />
        </nav>

        <div className="mt-auto space-y-4">
            {/* Last Refresh Indicator */}
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-xl text-xs text-slate-500">
                <RefreshCw size={12} className="animate-spin-slow" />
                <span>Auto-refresh: {lastRefresh.toLocaleTimeString()}</span>
            </div>
            <button onClick={() => authService.logout()} className="w-full flex items-center gap-4 p-4 text-red-500 font-bold hover:bg-red-50 rounded-2xl transition-colors">
                <LogOut size={20} /> <span className="text-sm">Log Out</span>
            </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-24 px-10 flex items-center justify-between border-b border-slate-100 bg-white/50 backdrop-blur-md">
            <div className="flex items-center gap-6">
                <h2 className="text-2xl font-black text-slate-900 capitalize">{activeTab}</h2>
            </div>
            <div className="flex items-center gap-4">
                <button onClick={fetchData} className="p-2 bg-slate-100 rounded-xl text-slate-500 hover:text-primary hover:bg-primary/10 transition-all">
                    <RefreshCw size={18} />
                </button>
                <div className="text-right">
                    <p className="text-sm font-bold text-slate-900">Municipal Admin</p>
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
                        <MapContainer center={userLocation} zoom={14} className="h-full w-full">
                            <TileLayer url={MAP_TILES} attribution={MAP_ATTRIBUTION} />
                            {mapMode === 'markers' ? (
                                issues.map(issue => (
                                    <Marker key={issue.id} position={[issue.lat, issue.lng]}>
                                        <Popup>
                                            <div className="p-3 w-64 space-y-3">
                                                <div className="flex justify-between items-start">
                                                    <p className="font-black text-slate-900">{issue.category_name}</p>
                                                    <span className="text-[9px] font-black uppercase text-primary px-1.5 py-0.5 bg-primary/5 rounded">{issue.status}</span>
                                                </div>
                                                {issue.eta_duration && (
                                                    <div className="flex items-center gap-1 text-amber-600 text-[10px] font-bold">
                                                        <Clock size={10} />
                                                        ETA: {issue.eta_duration}
                                                    </div>
                                                )}
                                                <div className="aspect-video bg-slate-100 rounded-lg overflow-hidden border">
                                                    <img src={`${API_URL}/media/${issue.id}/before`} className="w-full h-full object-cover" alt="Issue" />
                                                </div>
                                                <button onClick={() => setReviewIssue(issue)} className="w-full py-2 bg-primary text-white rounded-lg text-[10px] font-bold">Open Operations Console</button>
                                            </div>
                                        </Popup>
                                    </Marker>
                                ))
                            ) : ( <HeatmapLayer points={heatmapData} /> )}
                            <LocateControl />
                            <SearchField />
                        </MapContainer>
                    </div>
                </motion.div>
            )}

            {activeTab === 'kanban' && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col h-full gap-8">
                    {/* Worker Analytics Mini Section */}
                    <WorkerAnalyticsMini analytics={workerAnalytics} />
                    
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
                            { key: 'REPORTED', label: 'REPORTED', statuses: ['REPORTED'], color: 'bg-rose-500' },
                            { key: 'ASSIGNED', label: 'ASSIGNED', statuses: ['ASSIGNED', 'ACCEPTED'], color: 'bg-blue-500' },
                            { key: 'IN_PROGRESS', label: 'IN PROGRESS', statuses: ['IN_PROGRESS'], color: 'bg-amber-500' },
                            { key: 'RESOLVED', label: 'RESOLVED', statuses: ['RESOLVED'], color: 'bg-emerald-500' },
                            { key: 'CLOSED', label: 'CLOSED', statuses: ['CLOSED'], color: 'bg-slate-400' },
                        ].map(column => (
                            <div key={column.key} className="w-80 flex-shrink-0 flex flex-col gap-6">
                                <div className="flex items-center justify-between px-4">
                                    <div className="flex items-center gap-3">
                                        <div className={cn("w-2 h-2 rounded-full", column.color)}></div>
                                        <h3 className="font-black text-slate-600 text-sm tracking-widest">{column.label}</h3>
                                    </div>
                                    <span className="px-2 py-0.5 bg-slate-200 rounded-md text-[10px] font-black text-slate-500">{issues.filter(i => column.statuses.includes(i.status)).length}</span>
                                </div>
                                <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
                                    {issues.filter(i => column.statuses.includes(i.status)).map(issue => (
                                        <motion.div 
                                            key={issue.id} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                                            onClick={() => setReviewIssue(issue)}
                                            className={cn("bg-white p-6 rounded-[2rem] shadow-lg shadow-slate-200/40 border-2 transition-all relative group cursor-pointer ticket-card", selectedIssues.includes(issue.id) ? "border-primary" : "border-transparent")}
                                        >
                                            {column.key === 'REPORTED' && (
                                                <div className="absolute top-5 right-5 flex items-center gap-2">
                                                    <QuickAssignDropdown 
                                                        issue={issue} 
                                                        workers={workers}
                                                        onAssign={fetchData}
                                                    />
                                                    <input 
                                                        type="checkbox" checked={selectedIssues.includes(issue.id)}
                                                        className="w-5 h-5 rounded-md border-2 border-slate-200 checked:bg-primary transition-all cursor-pointer"
                                                        onChange={(e) => { e.stopPropagation(); toggleIssueSelection(issue.id); }}
                                                    />
                                                </div>
                                            )}
                                            <div className="flex gap-2 mb-4 flex-wrap">
                                                <span className={cn("text-[10px] font-black px-2 py-0.5 rounded-full", issue.priority === 'P1' ? "bg-rose-50 text-rose-600" : issue.priority === 'P2' ? "bg-amber-50 text-amber-600" : "bg-blue-50 text-blue-600")}>{issue.priority}</span>
                                                {issue.eta_duration && (
                                                    <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 flex items-center gap-1">
                                                        <Clock size={10} />
                                                        ETA: {issue.eta_duration}
                                                    </span>
                                                )}
                                            </div>
                                            <h4 className="font-black text-slate-900 text-lg mb-2 leading-tight group-hover:text-primary transition-colors">{issue.category_name}</h4>
                                            <p className="text-xs font-medium text-slate-400 line-clamp-2 mb-6">Issue #{issue.id.slice(0,8)} at {issue.address || 'Confirmed GPS Location'}.</p>
                                            <div className="flex items-center justify-between pt-4 border-t border-slate-50">
                                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
                                                    <Clock size={12} className="text-slate-300" />
                                                    <span>{new Date(issue.created_at).toLocaleDateString()}</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    {issue.worker_name && (
                                                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-tight truncate max-w-[80px]">{issue.worker_name}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}

            {activeTab === 'workers' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                    {/* Worker Analytics Mini Section */}
                    <WorkerAnalyticsMini analytics={workerAnalytics} />
                    
                    <div className="bg-white rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40 overflow-hidden">
                        <div className="p-8 border-b bg-slate-50/50 flex items-center justify-between">
                            <h3 className="text-xl font-black text-slate-900">Active Field Force</h3>
                            <div className="text-sm text-slate-500">
                                {workers.length} workers • {workers.reduce((sum, w) => sum + w.active_task_count, 0)} active tasks
                            </div>
                        </div>
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                                <tr>
                                    <th className="px-8 py-6">Member</th>
                                    <th className="px-8 py-6">Status</th>
                                    <th className="px-8 py-6">Active Tasks</th>
                                    <th className="px-8 py-6">Resolved</th>
                                    <th className="px-8 py-6">This Week</th>
                                    <th className="px-8 py-6">Performance</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {workers.map(worker => {
                                    // Find analytics for this worker
                                    const analytics = workerAnalytics?.workers?.find(w => w.worker_id === worker.id)
                                    return (
                                        <tr key={worker.id} className="hover:bg-slate-50/50 transition-colors">
                                            <td className="px-8 py-6">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-primary font-black shadow-sm">{worker.full_name?.[0] || 'W'}</div>
                                                    <div>
                                                        <p className="font-black text-slate-900">{worker.full_name || 'Unknown'}</p>
                                                        <p className="text-[10px] font-bold text-slate-400 uppercase">{worker.email}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <span className={cn(
                                                    "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider",
                                                    worker.status === 'ACTIVE' ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-500"
                                                )}>
                                                    {worker.status}
                                                </span>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="flex items-center gap-2">
                                                    <span className={cn(
                                                        "text-lg font-black",
                                                        worker.active_task_count === 0 ? "text-slate-300" :
                                                        worker.active_task_count <= 2 ? "text-blue-600" :
                                                        "text-amber-600"
                                                    )}>
                                                        {worker.active_task_count}
                                                    </span>
                                                    <span className="text-xs text-slate-400">tasks</span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <span className="text-lg font-black text-emerald-600">{worker.resolved_count}</span>
                                            </td>
                                            <td className="px-8 py-6">
                                                <span className="text-lg font-black text-purple-600">{analytics?.tasks_this_week || 0}</span>
                                            </td>
                                            <td className="px-8 py-6">
                                                {analytics?.avg_resolution_hours ? (
                                                    <div className="flex items-center gap-2">
                                                        <Zap size={14} className="text-amber-500" />
                                                        <span className="text-sm font-bold text-slate-600">
                                                            {analytics.avg_resolution_hours}h avg
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <span className="text-xs text-slate-400">No data</span>
                                                )}
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                </motion.div>
            )}
           </AnimatePresence>

           <AnimatePresence>
            {reviewIssue && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-[2000] flex items-center justify-center p-12">
                    <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} className="bg-white rounded-[3rem] w-full max-w-6xl flex flex-col h-[85vh] shadow-2xl overflow-hidden">
                        <div className="p-8 border-b flex justify-between items-center bg-white sticky top-0 z-10">
                            <div>
                                <h3 className="text-2xl font-black text-slate-900 tracking-tight">Infrastructure Intelligence Console</h3>
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                                    Incident Ticket #{reviewIssue.id.slice(0,8)} • Category: {reviewIssue.category_name}
                                    {reviewIssue.eta_duration && (
                                        <span className="ml-4 text-amber-600">• ETA: {reviewIssue.eta_duration}</span>
                                    )}
                                </p>
                            </div>
                            <button onClick={() => setReviewIssue(null)} className="w-12 h-12 rounded-full bg-slate-100 text-slate-500 hover:text-red-500 flex items-center justify-center transition-all">✕</button>
                        </div>
                        <div className="flex-1 flex flex-col lg:flex-row gap-8 p-10 overflow-auto bg-slate-50/50">
                            <div className="flex-1 flex flex-col gap-6">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 bg-rose-100 text-rose-600 rounded-lg flex items-center justify-center font-black text-[10px]">INITIAL</div>
                                        <h4 className="font-black text-slate-900">Before Reconstruction</h4>
                                    </div>
                                    <span className="text-[10px] font-black text-slate-400 uppercase">{new Date(reviewIssue.created_at).toLocaleString()}</span>
                                </div>
                                <div className="flex-1 bg-white rounded-[2.5rem] overflow-hidden border-8 border-white shadow-2xl">
                                    <img src={`${API_URL}/media/${reviewIssue.id}/before`} className="w-full h-full object-cover" alt="Before" />
                                </div>
                            </div>
                            <div className="flex-1 flex flex-col gap-6">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center font-black text-[10px]">FIELD</div>
                                        <h4 className="font-black text-slate-900">Resolution Verification</h4>
                                    </div>
                                    <span className="text-[10px] font-black text-emerald-500 uppercase">Real-Time Capture</span>
                                </div>
                                <div className="flex-1 bg-white rounded-[2.5rem] overflow-hidden border-8 border-emerald-50 shadow-2xl flex items-center justify-center">
                                    {reviewIssue.status === 'RESOLVED' || reviewIssue.status === 'CLOSED' ? (
                                        <img src={`${API_URL}/media/${reviewIssue.id}/after`} className="w-full h-full object-cover" alt="After" />
                                    ) : (
                                        <div className="text-center p-10 space-y-4">
                                            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto text-slate-200 shadow-inner"><Camera size={28} /></div>
                                            <p className="text-sm font-black text-slate-300 uppercase tracking-widest">Resolution Proof Pending</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                        
                        {/* Issue Details Panel */}
                        <div className="px-10 py-4 bg-slate-50 border-t border-slate-100">
                            <div className="flex items-center gap-8 text-sm">
                                <div>
                                    <span className="text-slate-400 text-xs uppercase font-bold">Assigned to:</span>
                                    <span className="ml-2 font-black text-slate-700">{reviewIssue.worker_name || 'Unassigned'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-400 text-xs uppercase font-bold">Status:</span>
                                    <span className="ml-2 font-black text-primary">{reviewIssue.status}</span>
                                </div>
                                {reviewIssue.eta_duration && (
                                    <div>
                                        <span className="text-slate-400 text-xs uppercase font-bold">ETA:</span>
                                        <span className="ml-2 font-black text-amber-600">{reviewIssue.eta_duration}</span>
                                    </div>
                                )}
                                {reviewIssue.accepted_at && (
                                    <div>
                                        <span className="text-slate-400 text-xs uppercase font-bold">Accepted:</span>
                                        <span className="ml-2 font-black text-slate-700">{new Date(reviewIssue.accepted_at).toLocaleString()}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                        
                        <div className="p-10 border-t flex items-center gap-8 bg-white">
                            <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Instructional feedback for the team..." className="flex-1 p-5 bg-slate-50 border-transparent rounded-2xl text-sm font-bold text-slate-900 outline-none focus:bg-white focus:ring-4 focus:ring-primary/5 transition-all resize-none h-20 shadow-inner" />
                            <div className="flex gap-4">
                                <button onClick={() => handleReject(reviewIssue.id)} disabled={submitting || !rejectReason} className="px-10 py-5 bg-rose-50 text-rose-600 font-black rounded-2xl hover:bg-rose-100 transition-all active:scale-95 border border-rose-100 shadow-sm disabled:opacity-50">Reject Proof</button>
                                <button onClick={() => handleApprove(reviewIssue.id)} disabled={submitting || (reviewIssue.status !== 'RESOLVED')} className="px-10 py-5 bg-primary text-white font-black rounded-2xl shadow-xl shadow-primary/20 hover:bg-blue-700 transition-all active:scale-95 disabled:opacity-50">Approve & Archive</button>
                            </div>
                        </div>
                    </motion.div>
                </motion.div>
            )}
           </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
