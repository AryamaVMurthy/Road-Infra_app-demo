import { useState, useEffect, useCallback } from 'react'
import api, { API_URL } from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { 
    Clock, ChevronRight, MapPin, ArrowLeft, Loader2, Info, X, 
    Camera, History, User, Map as MapIcon, ArrowRight, Activity 
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'
import Map, { Marker } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { EvidenceGallery } from '../../components/EvidenceGallery'
import { useAutoRefresh } from '../../hooks/useAutoRefresh'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example';

const StatusBadge = ({ status }) => {
  const styles = {
    REPORTED: 'bg-rose-50 text-rose-600 border-rose-100',
    ASSIGNED: 'bg-blue-50 text-blue-600 border-blue-100',
    IN_PROGRESS: 'bg-amber-50 text-amber-600 border-amber-100',
    RESOLVED: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    CLOSED: 'bg-slate-50 text-slate-500 border-slate-200',
    DISMISSED: 'bg-slate-50 text-slate-400 border-slate-100'
  }
  return (
    <span className={cn(
      "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider border shadow-sm", 
      styles[status] || styles.REPORTED
    )}>
      {status}
    </span>
  )
}

const TimelineItem = ({ log, isLast }) => (
    <div className="flex gap-6">
        <div className="flex flex-col items-center">
            <div className="w-10 h-10 rounded-2xl bg-white flex items-center justify-center text-primary border border-slate-100 shadow-sm shrink-0">
                <History size={18} />
            </div>
            {!isLast && <div className="w-0.5 h-full bg-slate-100 my-2"></div>}
        </div>
        <div className="pb-10 pt-1">
            <p className="text-xs font-black text-slate-900 uppercase tracking-[0.15em] mb-1.5">{log.action.replace('_', ' ')}</p>
            <p className="text-[12px] font-bold text-slate-400 mb-4 flex items-center gap-2">
                <Clock size={12} /> {new Date(log.created_at).toLocaleDateString()}
            </p>
            {log.new_value && (
                <div className="inline-flex items-center gap-3 px-4 py-2 bg-white rounded-xl border border-slate-100 shadow-sm text-[11px] font-bold">
                    <span className="text-slate-300 line-through decoration-slate-200">{log.old_value || 'Initial'}</span>
                    <ChevronRight size={12} className="text-slate-400" />
                    <span className="text-primary">{log.new_value}</span>
                </div>
            )}
        </div>
    </div>
)

function ReportMap({ report }) {
    if (!report.lat || !report.lng) return null;
    return (
        <Map
            initialViewState={{
                longitude: report.lng,
                latitude: report.lat,
                zoom: 16
            }}
            style={{ width: '100%', height: '100%' }}
            mapStyle="mapbox://styles/mapbox/streets-v12"
            mapboxAccessToken={MAPBOX_TOKEN}
        >
            <Marker longitude={report.lng} latitude={report.lat} />
        </Map>
    );
}

export default function MyReports() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedReport, setSelectedReport] = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [loadingAudit, setLoadingAudit] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const navigate = useNavigate()
  const { user } = useAuth()

  useEffect(() => {
    if (user) {
      fetchReports({ showLoader: true })
    }
  }, [user, fetchReports])

  const fetchReports = useCallback(async ({ showLoader = false } = {}) => {
    if (showLoader) {
      setLoading(true)
    }

    api.get('/issues/my-reports')
      .then(res => setReports(res.data))
      .catch((err) => {
        console.error('Failed to fetch reports', err)
      })
      .finally(() => {
        setLastRefresh(new Date())
        if (showLoader) {
          setLoading(false)
        }
      })
  }, [])

  useAutoRefresh(
    () => fetchReports({ showLoader: false }),
    { intervalMs: 45000, enabled: Boolean(user), runOnMount: false }
  )

  const handleViewDetails = async (report) => {
    setSelectedReport(report)
    setLoadingAudit(true)
    try {
        const res = await api.get(`/analytics/audit/${report.id}`)
        setAuditLogs(res.data)
    } catch (e) {
        console.error("Failed to load audit logs")
        setAuditLogs([])
    }
    setLoadingAudit(false)
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans">
      <header className="px-8 py-8 bg-white/80 backdrop-blur-xl border-b border-slate-100 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <button onClick={() => navigate('/citizen')} className="flex items-center gap-3 px-5 py-2.5 bg-slate-50 text-slate-600 font-bold rounded-2xl hover:bg-slate-100 hover:text-primary transition-all shadow-sm border border-slate-100">
          <ArrowLeft size={18} /> Home
        </button>
        <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary shadow-inner">
                <MapIcon size={20} />
            </div>
            <h1 className="text-xl font-black tracking-tight text-slate-900">Infrastructure Portal</h1>
        </div>
        <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-xl text-xs font-bold text-slate-500 border border-slate-100">
            <Clock size={12} />
            <span>Synced {lastRefresh.toLocaleTimeString()}</span>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full p-8 pb-32">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full text-[10px] font-black uppercase tracking-widest mb-4">
                <Activity size={12} /> Live Network Status
            </div>
            <h2 className="text-5xl font-black text-slate-900 mb-3 tracking-tight">Track Progress</h2>
            <p className="text-lg text-slate-500 font-medium">Monitoring the lifecycle of your infrastructure reports.</p>
        </motion.div>

        {loading ? (
            <div className="flex flex-col items-center justify-center py-32 gap-6">
                <div className="relative">
                    <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-primary animate-spin"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <MapPin size={24} className="text-primary" />
                    </div>
                </div>
                <p className="text-sm font-black text-slate-400 uppercase tracking-[0.2em]">Synchronizing Records...</p>
            </div>
        ) : reports.length === 0 ? (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-white p-20 rounded-[3.5rem] border border-slate-100 shadow-2xl shadow-slate-200/50 text-center">
                <div className="w-24 h-24 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-8 text-slate-200 shadow-inner">
                    <Info size={44} />
                </div>
                <h3 className="text-3xl font-black text-slate-900 mb-4">No Active Reports</h3>
                <p className="text-slate-400 font-bold text-lg mb-12 max-w-md mx-auto leading-relaxed">You haven&apos;t submitted any infrastructure issues in your jurisdiction yet.</p>
                <button onClick={() => navigate('/citizen/report')} className="px-12 py-6 bg-primary text-white font-black text-lg rounded-[2rem] shadow-2xl shadow-primary/30 hover:bg-blue-700 transition-all active:scale-95 flex items-center gap-3 mx-auto">
                   Report Your First Issue <ArrowRight size={22} />
                </button>
            </motion.div>
        ) : (
            <div className="space-y-10">
                {reports.map((report, idx) => (
                    <motion.div 
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.05 }}
                        key={report.id} 
                        onClick={() => handleViewDetails(report)}
                        className="bg-white p-10 rounded-[3.5rem] shadow-[0_32px_64px_-16px_rgba(0,0,0,0.06)] border border-white flex flex-col md:flex-row items-start md:items-center gap-10 group hover:border-primary/20 hover:shadow-primary/5 transition-all cursor-pointer relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-[80px] translate-x-20 -translate-y-20 group-hover:bg-primary/10 transition-colors"></div>

                        <div className="w-32 h-32 bg-slate-100 rounded-[2.5rem] overflow-hidden flex-shrink-0 border-8 border-slate-50 relative group-hover:scale-105 transition-transform shadow-xl">
                             <img src={`${API_URL}/media/${report.id}/before`} className="w-full h-full object-cover" alt="Issue" />
                             <div className="absolute inset-0 bg-black/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                <Camera size={32} className="text-white" />
                             </div>
                        </div>
                        <div className="flex-1 min-w-0 z-10">
                            <div className="flex flex-wrap items-center justify-between gap-6 mb-6">
                                <div className="space-y-1">
                                    <h3 className="text-2xl font-black text-slate-900 tracking-tight">Issue #{report.id.slice(0,8)}</h3>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Verified Ticket</p>
                                </div>
                                <StatusBadge status={report.status} />
                            </div>
                            <div className="flex flex-wrap items-center gap-x-8 gap-y-3 text-[14px] font-bold text-slate-400 mb-8">
                                <span className="flex items-center gap-2.5 text-slate-700 bg-slate-50 px-4 py-2 rounded-xl border border-slate-100">
                                    <MapPin size={18} className="text-primary"/> {report.address || 'Location Confirmed'}
                                </span>
                                <span className="flex items-center gap-2.5 text-slate-500">
                                    <Clock size={18}/> {new Date(report.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            
                            <div className="flex items-center gap-6">
                                <div className="flex -space-x-3">
                                    {[1,2].map(i => (
                                        <div key={i} className="w-10 h-10 rounded-2xl bg-slate-50 border-4 border-white shadow-sm flex items-center justify-center text-slate-300">
                                            <User size={16} />
                                        </div>
                                    ))}
                                </div>
                                <span className="text-[12px] font-black text-slate-500 uppercase tracking-[0.15em] pl-6 border-l-4 border-slate-100">
                                    {report.report_count} {report.report_count === 1 ? 'Report' : 'Reports'} Total
                                </span>
                            </div>
                        </div>
                        <button className="w-16 h-16 rounded-[2rem] bg-slate-50 flex items-center justify-center text-slate-300 group-hover:bg-primary group-hover:text-white group-hover:shadow-xl group-hover:shadow-primary/30 transition-all shadow-inner flex-shrink-0 self-end md:self-center active:scale-90">
                            <ChevronRight size={32} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                    </motion.div>
                ))}
            </div>
        )}

        <AnimatePresence>
            {selectedReport && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-slate-900/60 backdrop-blur-xl z-[2000] flex items-center justify-center p-6 sm:p-12">
                    <motion.div 
                        initial={{ scale: 0.9, y: 40, opacity: 0 }} 
                        animate={{ scale: 1, y: 0, opacity: 1 }} 
                        exit={{ scale: 0.9, y: 40, opacity: 0 }} 
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="bg-white rounded-[4rem] w-full max-w-6xl flex flex-col h-[90vh] shadow-[0_50px_100px_-20px_rgba(0,0,0,0.25)] overflow-hidden border border-white"
                    >
                        <div className="p-10 border-b border-slate-100 flex justify-between items-center bg-white/50 sticky top-0 z-20 backdrop-blur-xl">
                            <div className="flex items-center gap-6">
                                <div className="w-16 h-16 bg-primary rounded-[1.5rem] flex items-center justify-center text-white shadow-2xl shadow-primary/30">
                                    <Info size={32} />
                                </div>
                                <div>
                                    <h3 className="text-3xl font-black text-slate-900 tracking-tight">Incident Intelligence</h3>
                                    <p className="text-sm font-bold text-slate-400 tracking-[0.1em] uppercase">SYSTEM ID: {selectedReport.id}</p>
                                </div>
                            </div>
                            <button onClick={() => setSelectedReport(null)} className="w-14 h-14 rounded-3xl bg-slate-100 text-slate-500 hover:text-red-500 hover:bg-red-50 flex items-center justify-center transition-all shadow-inner">
                                <X size={28} />
                            </button>
                        </div>
                        
                        <div className="flex-1 overflow-auto p-12 custom-scrollbar space-y-16">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                                <div className="space-y-6">
                                    <div className="flex items-center justify-between px-2">
                                        <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Geospatial Marker</p>
                                        <div className="flex items-center gap-2 text-emerald-500 font-bold text-xs uppercase tracking-tighter">
                                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                            GPS Locked
                                        </div>
                                    </div>
                                    <div className="h-[400px] rounded-[3rem] overflow-hidden border-8 border-slate-50 shadow-2xl relative">
                                        <ReportMap report={selectedReport} />
                                        <div className="absolute bottom-6 left-6 right-6 bg-white/80 backdrop-blur-md p-5 rounded-2xl border border-white/20 shadow-xl z-[1000] flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className="p-2 bg-primary/10 text-primary rounded-lg shadow-inner"><MapPin size={18} /></div>
                                                <p className="text-[13px] font-bold text-slate-800 leading-tight truncate max-w-[200px]">{selectedReport.address || 'Gachibowli Node'}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-6">
                                    <EvidenceGallery issueId={selectedReport.id} status={selectedReport.status} apiUrl={API_URL} />
                                </div>
                            </div>

                            <div className="bg-slate-50/50 rounded-[3.5rem] p-12 border border-slate-100 shadow-inner relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[100px] -mr-32 -mt-32"></div>
                                
                                <div className="flex items-center gap-4 mb-12">
                                    <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-primary shadow-sm border border-slate-100">
                                        <History size={24} />
                                    </div>
                                    <div>
                                        <h4 className="text-2xl font-black text-slate-900 tracking-tight">Audit History</h4>
                                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Temporal Log</p>
                                    </div>
                                </div>
                                
                                <div className="space-y-2">
                                    {loadingAudit ? (
                                        <div className="flex flex-col items-center justify-center py-10 gap-4">
                                            <Loader2 size={24} className="animate-spin text-primary" />
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Querying Audit Node...</p>
                                        </div>
                                    ) : auditLogs.length === 0 ? (
                                        <div className="text-center py-10">
                                            <p className="text-sm font-black text-slate-300 uppercase tracking-widest">No mutation logs found for this entity</p>
                                        </div>
                                    ) : (
                                        auditLogs.map((log, idx) => (
                                            <TimelineItem key={log.id} log={log} isLast={idx === auditLogs.length - 1} />
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="p-10 border-t bg-white flex flex-col sm:flex-row items-center justify-between gap-8 sticky bottom-0 z-20">
                            <div className="flex items-center gap-6">
                                <div className="w-16 h-16 bg-slate-50 rounded-[1.5rem] flex items-center justify-center text-slate-400 border border-slate-100 shadow-inner">
                                    <User size={32} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1">Issue Custodian</p>
                                    <p className="text-lg font-black text-slate-900">{selectedReport.worker_name || 'Authority Dispatcher'}</p>
                                </div>
                            </div>
                            <div className="flex gap-4 w-full sm:w-auto">
                                <button onClick={() => setSelectedReport(null)} className="flex-1 sm:flex-none px-10 py-5 bg-primary text-white font-black rounded-3xl shadow-2xl shadow-primary/30 hover:bg-blue-800 transition-all active:scale-95">
                                    Close Portal
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
        
        <div className="mt-16 p-10 bg-primary/5 rounded-[3.5rem] border border-primary/10 relative overflow-hidden">
            <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center gap-8">
                <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center text-white shadow-xl shadow-primary/20">
                    <Info size={32} />
                </div>
                <div>
                    <h3 className="text-2xl font-black text-slate-900 mb-2">Community Impact</h3>
                    <p className="text-[15px] text-slate-600 font-medium leading-relaxed max-w-2xl">
                        By reporting issues, you are helping the authority optimize resources and fix infrastructure more efficiently. Thank you for making our city safer.
                    </p>
                </div>
            </div>
            <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-primary/10 rounded-full blur-3xl"></div>
        </div>
      </main>
    </div>
  )
}
