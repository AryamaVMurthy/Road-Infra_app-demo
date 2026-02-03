import React, { useState, useEffect } from 'react'
import api, { API_URL } from '../../services/api'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { 
    LayoutDashboard, Map as MapIcon, Users, LogOut, Filter, 
    ChevronDown, CheckCircle2, AlertCircle, Clock,
    CheckSquare, XCircle, Camera, Info, X, MapPin, ChevronRight, Activity, Globe
} from 'lucide-react'
import { authService } from '../../services/auth'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'

import { HeatmapLayer } from '../../components/HeatmapLayer'
import { LocateControl } from '../../components/LocateControl'
import { SearchField } from '../../components/SearchField'

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

const StatCard = ({ label, value, icon: Icon, colorClass }) => (
    <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 flex items-center gap-6">
        <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center text-white", colorClass)}>
            <Icon size={24} />
        </div>
        <div>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">{label}</p>
            <p className="text-3xl font-extrabold text-slate-900">{value}</p>
        </div>
    </div>
)

export default function AuthorityDashboard() {
  const [activeTab, setActiveTab] = useState('map') 
  const [issues, setIssues] = useState([])
  const [workers, setWorkers] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedIssues, setSelectedIssues] = useState([])
  const [reviewIssue, setReviewIssue] = useState(null)
  const [mapMode, setMapMode] = useState('markers')
  const [heatmapData, setHeatmapData] = useState([])
  const [rejectReason, setRejectReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [userLocation, setUserLocation] = useState([17.4447, 78.3483])
  const navigate = useNavigate()

  useEffect(() => { 
    fetchData()
    navigator.geolocation.getCurrentPosition(
      (pos) => setUserLocation([pos.coords.latitude, pos.coords.longitude]),
      () => {}
    )
  }, [])

  const fetchData = () => {
    setLoading(true)
    Promise.all([
      api.get('/admin/issues'), 
      api.get('/admin/workers'),
      api.get('/analytics/heatmap')
    ]).then(([issuesRes, workersRes, heatRes]) => {
        setIssues(issuesRes.data)
        setWorkers(workersRes.data)
        setHeatmapData(heatRes.data)
      }).catch(() => {})
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
                            <StatCard label="Live Issues" value={issues.length} icon={AlertCircle} colorClass="bg-rose-500 shadow-rose-200/50" />
                            <StatCard label="In Field" value={workers.length} icon={Users} colorClass="bg-blue-500 shadow-blue-200/50" />
                            <StatCard label="Resolved" value={issues.filter(i => i.status === 'RESOLVED' || i.status === 'CLOSED').length} icon={CheckCircle2} colorClass="bg-emerald-500 shadow-emerald-200/50" />
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
                    {selectedIssues.length > 0 && (
                        <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} className="flex items-center gap-4 px-6 py-2 bg-primary rounded-2xl shadow-xl shadow-primary/30">
                            <span className="text-sm font-black text-white">{selectedIssues.length} SELECTED</span>
                            <select 
                                className="bg-white/10 text-white border-none rounded-lg text-xs font-bold py-1.5 focus:ring-0 outline-none"
                                onChange={(e) => handleBulkAssign(e.target.value)} value=""
                            >
                                <option value="" className="text-black">Assign to...</option>
                                {workers.map(w => <option key={w.id} value={w.id} className="text-black">{w.full_name}</option>)}
                            </select>
                            <button onClick={() => setSelectedIssues([])} className="text-white/60 hover:text-white transition-colors"><XCircle size={18}/></button>
                        </motion.div>
                    )}
                    
                    <div className="flex gap-8 overflow-x-auto pb-6 h-full">
                        {['REPORTED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED'].map(status => (
                            <div key={status} className="w-80 flex-shrink-0 flex flex-col gap-6">
                                <div className="flex items-center justify-between px-4">
                                    <div className="flex items-center gap-3">
                                        <div className={cn("w-2 h-2 rounded-full", 
                                            status === 'REPORTED' ? "bg-rose-500" : status === 'ASSIGNED' ? "bg-blue-500" : status === 'IN_PROGRESS' ? "bg-amber-500" : "bg-emerald-500"
                                        )}></div>
                                        <h3 className="font-black text-slate-600 text-sm tracking-widest">{status}</h3>
                                    </div>
                                    <span className="px-2 py-0.5 bg-slate-200 rounded-md text-[10px] font-black text-slate-50">{issues.filter(i => i.status === status).length}</span>
                                </div>
                                <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
                                    {issues.filter(i => i.status === status).map(issue => (
                                        <motion.div 
                                            key={issue.id} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                                            onClick={() => setReviewIssue(issue)}
                                            className={cn("bg-white p-6 rounded-[2rem] shadow-lg shadow-slate-200/40 border-2 transition-all relative group cursor-pointer ticket-card", selectedIssues.includes(issue.id) ? "border-primary" : "border-transparent")}
                                        >
                                            {status === 'REPORTED' && (
                                                <input 
                                                    type="checkbox" checked={selectedIssues.includes(issue.id)}
                                                    className="absolute top-6 right-6 w-5 h-5 rounded-md border-2 border-slate-200 checked:bg-primary transition-all cursor-pointer"
                                                    onChange={(e) => { e.stopPropagation(); toggleIssueSelection(issue.id); }}
                                                />
                                            )}
                                            <div className="flex gap-2 mb-4">
                                                <span className={cn("text-[10px] font-black px-2 py-0.5 rounded-full", issue.priority === 'P1' ? "bg-rose-50 text-rose-600" : "bg-blue-50 text-blue-600")}>{issue.priority}</span>
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
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40 overflow-hidden">
                    <div className="p-8 border-b bg-slate-50/50">
                        <h3 className="text-xl font-black text-slate-900">Active Field Force</h3>
                    </div>
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                            <tr>
                                <th className="px-8 py-6">Member</th>
                                <th className="px-8 py-6">Status</th>
                                <th className="px-8 py-6">Current Workload</th>
                                <th className="px-8 py-6">Performance</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {workers.map(worker => (
                                <tr key={worker.id} className="hover:bg-slate-50/50 transition-colors">
                                    <td className="px-8 py-6">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-primary font-black shadow-sm">{worker.full_name[0]}</div>
                                            <div>
                                                <p className="font-black text-slate-900">{worker.full_name}</p>
                                                <p className="text-[10px] font-bold text-slate-400 uppercase">{worker.email}</p>
                                            </div>
                                        </div>
                                    </td>
                                            <td className="px-8 py-6"><span className="px-3 py-1 bg-emerald-50 text-emerald-600 rounded-full text-[10px] font-black uppercase tracking-wider">Active</span></td>
                                            <td className="px-8 py-6 text-sm font-bold text-slate-600">Tasks assigned</td>
                                            <td className="px-8 py-6"><span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-[10px] font-black uppercase tracking-wider">On Duty</span></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
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
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Incident Ticket #{reviewIssue.id.slice(0,8)} • Category: {reviewIssue.category_name}</p>
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
