import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import {
    Settings, Shield, Globe, Activity, Database, LogOut,
    TrendingUp, Users, AlertTriangle, CheckCircle,
    ChevronRight, ArrowRight, Building2, Layers, Zap, UserPlus, RefreshCw,
    CheckCircle2, ArrowLeft, ShieldCheck, Clock
} from 'lucide-react'
import { authService } from '../../services/auth'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import {
    Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
    AreaChart, Area, XAxis, YAxis, CartesianGrid
} from 'recharts'
import { useNavigate } from 'react-router-dom'
import Map, { Marker, Popup } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { MapboxHeatmap } from '../../components/MapboxHeatmap'
import { MapboxLocateControl } from '../../components/MapboxLocateControl'
import { MapboxGeocoderControl } from '../../components/MapboxGeocoder'
import { MapErrorBoundary, MapTokenGuard } from '../../components/MapSafeGuard'
import { useGeolocation, DEFAULT_CENTER } from '../../hooks/useGeolocation'

const OnboardWorkerModal = ({ isOpen, onClose, organizations, onCreated }) => {
    const [form, setForm] = useState({ email: '', full_name: '', org_id: '' })
    const [submitting, setSubmitting] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setSubmitting(true)
        try {
            await api.post('/admin/onboard', { ...form, role: 'WORKER' })
            alert('Worker Onboarded Successfully')
            onCreated()
            onClose()
        } catch (err) {
            alert('Failed to onboard worker')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose} className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" 
                    />
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white rounded-[2.5rem] w-full max-w-lg overflow-hidden shadow-2xl relative z-10"
                    >
                        <div className="p-8 border-b bg-slate-50">
                            <h3 className="text-xl font-black text-slate-900">Add Field Force</h3>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mt-1">Worker Onboarding</p>
                        </div>
                        <form onSubmit={handleSubmit} className="p-8 space-y-6">
                            <div className="space-y-4">
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Worker Email</label>
                                    <input 
                                        type="email" required value={form.email} 
                                        onChange={e => setForm({...form, email: e.target.value})}
                                        className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        placeholder="worker@authority.gov.in"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
                                    <input 
                                        type="text" required value={form.full_name} 
                                        onChange={e => setForm({...form, full_name: e.target.value})}
                                        className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        placeholder="John Smith"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Assign Organization</label>
                                    <select 
                                        value={form.org_id} onChange={e => setForm({...form, org_id: e.target.value})}
                                        className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        required
                                    >
                                        <option value="">Select Org</option>
                                        {organizations.map(org => (
                                            <option key={org.id} value={org.id}>{org.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <button 
                                type="submit" disabled={submitting}
                                className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-slate-800 transition-all disabled:opacity-50 shadow-xl shadow-slate-900/20"
                            >
                                {submitting ? 'Onboarding...' : 'Register Worker'}
                            </button>
                        </form>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}

const CategoryModal = ({ isOpen, onClose, onCreated }) => {
    const [form, setForm] = useState({ name: '', default_priority: 'P3', expected_sla_days: 3 })
    const [submitting, setSubmitting] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setSubmitting(true)
        try {
            await api.post('/admin/categories', form)
            alert('Category Created Successfully')
            onCreated()
            onClose()
        } catch (err) {
            alert('Failed to create category')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose} className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" 
                    />
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white rounded-[2.5rem] w-full max-w-lg overflow-hidden shadow-2xl relative z-10"
                    >
                        <div className="p-8 border-b bg-slate-50">
                            <h3 className="text-xl font-black text-slate-900">Add New Category</h3>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mt-1">Classification Registry</p>
                        </div>
                        <form onSubmit={handleSubmit} className="p-8 space-y-6">
                            <div className="space-y-4">
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Category Name</label>
                                    <input 
                                        type="text" required value={form.name} 
                                        onChange={e => setForm({...form, name: e.target.value})}
                                        className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        placeholder="e.g. Water Leakage"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Default Priority</label>
                                        <select 
                                            value={form.default_priority} onChange={e => setForm({...form, default_priority: e.target.value})}
                                            className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        >
                                            <option value="P1">P1 - Critical</option>
                                            <option value="P2">P2 - High</option>
                                            <option value="P3">P3 - Medium</option>
                                            <option value="P4">P4 - Low</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">SLA (Days)</label>
                                        <input 
                                            type="number" required value={form.expected_sla_days} 
                                            onChange={e => setForm({...form, expected_sla_days: parseInt(e.target.value)})}
                                            className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                            min="1"
                                        />
                                    </div>
                                </div>
                            </div>
                            <button 
                                type="submit" disabled={submitting}
                                className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-slate-800 transition-all disabled:opacity-50 shadow-xl shadow-slate-900/20"
                            >
                                {submitting ? 'Adding...' : 'Add Category'}
                            </button>
                        </form>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}

const CategoryDetailsModal = ({ isOpen, onClose, category }) => {
    if (!category) return null;
    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose} className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" 
                    />
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white rounded-[2.5rem] w-full max-w-md overflow-hidden shadow-2xl relative z-10"
                    >
                        <div className="p-8 border-b bg-slate-50 flex justify-between items-center">
                            <div>
                                <h3 className="text-xl font-black text-slate-900">{category.name}</h3>
                                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mt-1">Registry Details</p>
                            </div>
                            <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center text-white", 
                                category.default_priority === 'P1' ? 'bg-rose-500' : 
                                category.default_priority === 'P2' ? 'bg-orange-500' : 
                                category.default_priority === 'P3' ? 'bg-blue-500' : 'bg-slate-500'
                            )}>
                                <span className="font-black text-xs">{category.default_priority}</span>
                            </div>
                        </div>
                        <div className="p-8 space-y-6">
                            <div className="grid grid-cols-2 gap-8">
                                <div>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Expected SLA</p>
                                    <p className="text-lg font-black text-slate-900">{category.expected_sla_days} Days</p>
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Status</p>
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                                        <p className="text-lg font-black text-slate-900">Active</p>
                                    </div>
                                </div>
                            </div>
                            <div className="pt-4 border-t border-slate-50">
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Recent Activity</p>
                                <div className="bg-slate-50 rounded-2xl p-4 text-xs font-bold text-slate-500 text-center italic">
                                    No localized anomalies detected for this category in the last 24h.
                                </div>
                            </div>
                        </div>
                        <div className="p-8 pt-0">
                            <button 
                                onClick={onClose}
                                className="w-full py-4 bg-slate-100 text-slate-900 rounded-2xl font-black uppercase tracking-widest text-[10px] hover:bg-slate-200 transition-all"
                            >
                                Close Inspector
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}

const DiagnosticsModal = ({ isOpen, onClose }) => {
    const [results, setResults] = useState(null)
    const [loading, setLoading] = useState(false)

    const runDiagnostics = async () => {
        setLoading(true)
        try {
            const res = await api.get('/admin/diagnostics')
            setResults(res.data)
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (isOpen) runDiagnostics()
    }, [isOpen])

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose} className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white rounded-[2.5rem] w-full max-w-2xl overflow-hidden shadow-2xl relative z-10"
                    >
                        <div className="p-8 border-b flex justify-between items-center bg-slate-50">
                            <div>
                                <h3 className="text-xl font-black text-slate-900">System Integrity Scan</h3>
                                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mt-1">Real-time Platform Diagnostics</p>
                            </div>
                            <button onClick={onClose} className="w-10 h-10 rounded-full hover:bg-slate-200 flex items-center justify-center transition-colors">
                                <LogOut size={20} className="rotate-90" />
                            </button>
                        </div>
                        <div className="p-8 space-y-6">
                            {loading ? (
                                <div className="flex flex-col items-center justify-center py-12 gap-4">
                                    <RefreshCw className="animate-spin text-primary" size={40} />
                                    <p className="font-black text-slate-400 uppercase tracking-widest text-xs">Pinging Infrastructure...</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {results?.results.map((r) => (
                                        <div key={r.name} className="flex items-center justify-between p-6 bg-slate-50 rounded-2xl border border-slate-100">
                                            <div className="flex items-center gap-4">
                                                <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center text-white", r.status === 'HEALTHY' ? 'bg-emerald-500' : 'bg-rose-500')}>
                                                    {r.status === 'HEALTHY' ? <CheckCircle size={20} /> : <AlertTriangle size={20} />}
                                                </div>
                                                <div>
                                                    <p className="font-black text-slate-900">{r.name}</p>
                                                    <p className="text-xs font-medium text-slate-500">{r.message}</p>
                                                </div>
                                            </div>
                                            <div className={cn("px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest", r.status === 'HEALTHY' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700')}>
                                                {r.status}
                                            </div>
                                        </div>
                                    ))}
                                    <div className="pt-6 text-center text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">
                                        Last Scan: {results?.timestamp && new Date(results.timestamp).toLocaleString()}
                                    </div>
                                </div>
                            )}
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}

const OnboardModal = ({ isOpen, onClose, organizations }) => {
    const [form, setForm] = useState({ email: '', full_name: '', role: 'ADMIN', org_id: '' })
    const [submitting, setSubmitting] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setSubmitting(true)
        try {
            await api.post('/admin/onboard', form)
            alert('Authority Onboarded Successfully')
            onClose()
        } catch (err) {
            alert('Failed to onboard authority')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose} className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white rounded-[2.5rem] w-full max-w-lg overflow-hidden shadow-2xl relative z-10"
                    >
                        <div className="p-8 border-b bg-slate-50">
                            <h3 className="text-xl font-black text-slate-900">Provision New Node</h3>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mt-1">Authority Onboarding</p>
                        </div>
                        <form onSubmit={handleSubmit} className="p-8 space-y-6">
                            <div className="space-y-4">
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Email Address</label>
                                    <input
                                        type="email" required value={form.email}
                                        onChange={e => setForm({ ...form, email: e.target.value })}
                                        className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        placeholder="authority@gov.in"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
                                    <input
                                        type="text" required value={form.full_name}
                                        onChange={e => setForm({ ...form, full_name: e.target.value })}
                                        className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        placeholder="John Doe"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">System Role</label>
                                        <select
                                            value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}
                                            className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                        >
                                            <option value="ADMIN">Authority Admin</option>
                                            <option value="SYSADMIN">System Admin</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Organization</label>
                                        <select
                                            value={form.org_id} onChange={e => setForm({ ...form, org_id: e.target.value })}
                                            className="w-full mt-1.5 p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary/20 outline-none font-bold text-slate-900 transition-all"
                                            required={form.role === 'ADMIN'}
                                        >
                                            <option value="">Select Org</option>
                                            {organizations.map(org => (
                                                <option key={org.id} value={org.id}>{org.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <button
                                type="submit" disabled={submitting}
                                className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-slate-800 transition-all disabled:opacity-50 shadow-xl shadow-slate-900/20"
                            >
                                {submitting ? 'Provisioning...' : 'Initialize Authority'}
                            </button>
                        </form>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}

const AdminStat = ({ label, value, trend, icon: Icon, color }) => (
    <motion.div whileHover={{ y: -5 }} className="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
        <div className="flex justify-between items-start mb-6">
            <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center text-white shadow-lg", color)}>
                <Icon size={24} />
            </div>
            {trend && (
                <div className="flex items-center gap-1 text-green-500 font-black text-xs bg-green-50 px-2 py-1 rounded-full">
                    <TrendingUp size={12} /> {trend}
                </div>
            )}
        </div>
        <p className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-1">{label}</p>
        <p className="text-4xl font-black text-slate-900">{value}</p>
        <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-slate-50 rounded-full group-hover:scale-150 transition-transform duration-500 opacity-50"></div>
    </motion.div>
)

export default function AdminDashboard() {
    const [activeTab, setActiveTab] = useState('summary')
    const [data, setData] = useState(null)
    const [audits, setAudits] = useState([])
    const [organizations, setOrganizations] = useState([])
    const [categories, setCategories] = useState([])
    const [zones, setZones] = useState([])
    const [heatmapData, setHeatmapData] = useState([])
    const [mapIssues, setMapIssues] = useState([])
    const [loading, setLoading] = useState(true)
    const [showDiagnostics, setShowDiagnostics] = useState(false)
    const [showOnboard, setShowOnboard] = useState(false)
    const [showOnboardWorker, setShowOnboardWorker] = useState(false)
    const [showAddCategory, setShowAddCategory] = useState(false)
    const [selectedCategory, setSelectedCategory] = useState(null)
    const [analyticsViewMode, setAnalyticsViewMode] = useState('heatmap')
    const navigate = useNavigate()

    const { position: geoPosition } = useGeolocation()
    const userLocation = geoPosition ? [geoPosition.lat, geoPosition.lng] : [DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]
    const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example';

    const fetchAdminData = useCallback(() => {
        setLoading(true)
        const promises = [
            api.get('/admin/issues'),
            api.get('/admin/workers'),
            api.get('/analytics/stats'),
            api.get('/admin/categories'),
            api.get('/admin/organizations'),
            api.get('/admin/zones')
        ]

        if (activeTab === 'audit') {
            promises.push(api.get('/analytics/audit-all').catch(() => ({ data: [] })))
        } else if (activeTab === 'analytics') {
            promises.push(api.get('/analytics/heatmap').catch(() => ({ data: [] })))
            promises.push(api.get('/analytics/issues-public').catch(() => ({ data: [] })))
        }

        Promise.allSettled(promises).then((results) => {
            if (results[2].status === 'fulfilled') setData(results[2].value.data);
            if (results[3].status === 'fulfilled') setCategories(results[3].value.data);
            if (results[4].status === 'fulfilled') setOrganizations(results[4].value.data);
            if (results[5].status === 'fulfilled') setZones(results[5].value.data);

            if (activeTab === 'audit' && results[6]?.status === 'fulfilled') {
                setAudits(results[6].value.data);
            }
            if (activeTab === 'analytics') {
                if (results[6]?.status === 'fulfilled') setHeatmapData(results[6].value.data);
                if (results[7]?.status === 'fulfilled') setMapIssues(results[7].value.data);
            }
        }).finally(() => setLoading(false));
    }, [activeTab])

    useEffect(() => {
        fetchAdminData()
    }, [fetchAdminData])

    const stats = [
        { name: 'Total Issues', value: data?.summary.reported || 0, color: 'bg-rose-500', icon: AlertTriangle },
        { name: 'Active Workers', value: data?.summary.workers || 0, color: 'bg-blue-500', icon: Users },
        { name: 'Resolved', value: data?.summary.resolved || 0, color: 'bg-emerald-500', icon: CheckCircle },
        { name: 'Compliance', value: data?.summary.compliance || '0%', color: 'bg-purple-500', icon: Shield },
    ]

    return (
        <div className="flex h-screen bg-[#F8FAFC]">
            <aside className="w-80 bg-slate-950 text-white flex flex-col p-8">
                <div className="flex items-center gap-4 mb-16">
                    <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-slate-950 shadow-xl shadow-white/10">
                        <Shield size={28} />
                    </div>
                    <div>
                        <h1 className="text-xl font-black tracking-tight leading-none">MARG</h1>
                    </div>
                </div>

                <nav className="flex-1 space-y-3">
                    <button onClick={() => setActiveTab('summary')} className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", activeTab === 'summary' ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}>
                        <Activity size={20} /> <span className="text-sm">Summary</span>
                    </button>
                    <button onClick={() => setActiveTab('analytics')} className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", activeTab === 'analytics' ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}>
                        <Globe size={20} /> <span className="text-sm">Full Analytics</span>
                    </button>
                    <button onClick={() => setActiveTab('config')} className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", activeTab === 'config' ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}>
                        <Settings size={20} /> <span className="text-sm">System Config</span>
                    </button>
                    <button onClick={() => setActiveTab('audit')} className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", activeTab === 'audit' ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}>
                        <Database size={20} /> <span className="text-sm">Audit Trails</span>
                    </button>
                </nav>

                <div className="mt-auto pt-8 border-t border-white/5">
                    <button onClick={() => authService.logout()} className="w-full flex items-center gap-4 p-5 text-red-400 font-bold hover:bg-red-500/10 rounded-[1.5rem] transition-all">
                        <LogOut size={20} /> <span className="text-sm">Exit System</span>
                    </button>
                </div>
            </aside>

            <div className="flex-1 flex flex-col overflow-hidden">
                <header className="h-28 px-12 flex items-center justify-between bg-white/50 backdrop-blur-md">
                    <div>
                        <h2 className="text-3xl font-black text-slate-900 tracking-tight capitalize">{activeTab.replace('-', ' ')}</h2>
                    </div>
                    <div className="flex items-center gap-4 pl-6 border-l border-slate-200">
                        <div className="text-right">
                            <p className="text-sm font-black text-slate-900">Chief Officer</p>
                            <p className="text-[10px] font-bold text-emerald-500 uppercase tracking-tighter">Verified Node</p>
                        </div>
                        <div className="w-14 h-14 bg-slate-900 rounded-[1.5rem] flex items-center justify-center text-white font-black shadow-lg">CO</div>
                    </div>
                </header>

                <main className="flex-1 overflow-auto p-12 pt-4">
                    <AnimatePresence mode="wait">
                        {activeTab === 'summary' && (
                            <motion.div key="summary" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
                                    {stats.map((s) => (
                                        <AdminStat key={s.name} label={s.name} value={s.value} trend={s.trend} icon={s.icon} color={s.color} />
                                    ))}
                                </div>

                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mb-12">
                                    <div className="bg-white p-10 rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40">
                                        <h3 className="text-xl font-black text-slate-900 mb-2">Category Split</h3>
                                        <div className="h-[280px]">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <PieChart>
                                                    <Pie
                                                        data={data?.category_split || []}
                                                        innerRadius={80}
                                                        outerRadius={110}
                                                        paddingAngle={8}
                                                        dataKey="value"
                                                        stroke="none"
                                                    >
                                                        {(data?.category_split || []).map((entry, index) => (
                                                            <Cell key={entry.name ?? `cell-${index}`} fill={['#3B82F6', '#EF4444', '#F59E0B', '#10B981'][index % 4]} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                        <div className="space-y-4 mt-8">
                                            {(data?.category_split || []).map((d, i) => (
                                                <div key={d.name} className="flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: ['#3B82F6', '#EF4444', '#F59E0B', '#10B981'][i % 4] }}></div>
                                                        <span className="text-sm font-bold text-slate-600 uppercase tracking-tighter">{d.name}</span>
                                                    </div>
                                                    <span className="text-sm font-black text-slate-900">{d.value}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    <motion.div
                                        whileHover={{ scale: 1.01 }}
                                        onClick={() => setActiveTab('analytics')}
                                        className="bg-primary rounded-[3rem] p-12 text-white flex flex-col justify-center relative overflow-hidden cursor-pointer group shadow-2xl shadow-primary/20"
                                    >
                                        <div className="relative z-10 space-y-6">
                                            <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-md border border-white/10 group-hover:scale-110 transition-transform">
                                                <Globe size={32} />
                                            </div>
                                            <div className="space-y-2">
                                                <h3 className="text-4xl font-black tracking-tight">Intelligence Center</h3>
                                                <p className="text-blue-100 font-medium text-lg leading-relaxed">
                                                    Enter the full geospatial analytics engine to view city-wide hotspots, heatmaps, and temporal growth analysis.
                                                </p>
                                            </div>
                                            <div className="pt-6 flex items-center gap-3 font-black uppercase tracking-widest text-xs">
                                                <span>Enter Control Plane</span>
                                                <ArrowRight size={18} className="group-hover:translate-x-2 transition-transform" />
                                            </div>
                                        </div>
                                        <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-white/10 rounded-full blur-[100px]"></div>
                                    </motion.div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'analytics' && (
                            <motion.div key="analytics" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-12 pb-12">
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                                    <div className="lg:col-span-2 bg-white rounded-[3.5rem] p-10 border border-slate-100 shadow-2xl relative overflow-hidden h-[600px] flex flex-col">
                                        <div className="flex items-center justify-between mb-8 px-2">
                                            <div className="space-y-1">
                                                <h3 className="text-2xl font-black text-slate-900">Geospatial Insights</h3>
                                                <p className="text-sm font-bold text-slate-400 uppercase tracking-tighter">Live Municipal Analysis</p>
                                            </div>
                                            <div className="flex bg-slate-100 p-1 rounded-2xl border shadow-inner">
                                                <button
                                                    onClick={() => setAnalyticsViewMode('heatmap')}
                                                    className={cn("px-4 py-2 rounded-xl text-[10px] font-black uppercase transition-all", analyticsViewMode === 'heatmap' ? "bg-primary text-white shadow-md" : "text-slate-500 hover:text-slate-900")}
                                                >
                                                    Heatmap
                                                </button>
                                                <button
                                                    onClick={() => setAnalyticsViewMode('markers')}
                                                    className={cn("px-4 py-2 rounded-xl text-[10px] font-black uppercase transition-all", analyticsViewMode === 'markers' ? "bg-primary text-white shadow-md" : "text-slate-500 hover:text-slate-900")}
                                                >
                                                    Live Markers
                                                </button>
                                            </div>
                                        </div>
                                        <div className="flex-1 rounded-[2.5rem] overflow-hidden border-8 border-slate-50 shadow-inner relative">
                                            <MapErrorBoundary>
                                                <MapTokenGuard token={MAPBOX_TOKEN}>
                                                    <Map
                                                        initialViewState={{
                                                            longitude: userLocation[1],
                                                            latitude: userLocation[0],
                                                            zoom: 12
                                                        }}
                                                        style={{ width: '100%', height: '100%' }}
                                                        mapStyle="mapbox://styles/mapbox/streets-v12"
                                                        mapboxAccessToken={MAPBOX_TOKEN}
                                                    >
                                                        {analyticsViewMode === 'heatmap' ? (
                                                            <MapboxHeatmap points={heatmapData} />
                                                        ) : (
                                                            mapIssues.map(issue => (
                                                                <Marker key={issue.id} longitude={issue.lng} latitude={issue.lat}>
                                                                    <Popup
                                                                        longitude={issue.lng}
                                                                        latitude={issue.lat}
                                                                        closeButton={true}
                                                                        closeOnClick={false}
                                                                    >
                                                                        <div className="p-2 space-y-2">
                                                                            <p className="font-black text-slate-900">{issue.category_name}</p>
                                                                            <p className="text-xs text-slate-500">{issue.status}</p>
                                                                        </div>
                                                                    </Popup>
                                                                </Marker>
                                                            ))
                                                        )}
                                                        <MapboxLocateControl />
                                                        <MapboxGeocoderControl mapboxAccessToken={MAPBOX_TOKEN} />
                                                    </Map>
                                                </MapTokenGuard>
                                            </MapErrorBoundary>
                                        </div>
                                    </div>

                                    <div className="space-y-12">
                                        <div className="bg-slate-900 rounded-[3rem] p-10 text-white relative overflow-hidden shadow-2xl shadow-slate-900/40">
                                            <div className="relative z-10 space-y-6">
                                                <div className="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center text-primary border border-white/5 shadow-inner">
                                                    <Zap size={24} />
                                                </div>
                                                <h3 className="text-2xl font-black tracking-tight">Incident Trends</h3>
                                                <div className="space-y-4">
                                                    <div className="flex justify-between items-end">
                                                        <p className="text-xs font-bold text-slate-400">ACTIVE ISSUES</p>
                                                        <p className="text-xl font-black text-emerald-400">{(data?.summary.reported || 0) - (data?.summary.resolved || 0)}</p>
                                                    </div>
                                                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                                        <div className="h-full bg-primary" style={{ width: `${data?.summary.reported > 0 ? ((data?.summary.resolved || 0) / data?.summary.reported * 100) : 0}%` }}></div>
                                                    </div>
                                                    <p className="text-[10px] font-medium text-slate-500 leading-relaxed">
                                                        Resolution progress based on real-time municipal data.
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-primary/20 rounded-full blur-3xl"></div>
                                        </div>

                                        <section className="bg-white p-10 rounded-[3rem] border border-slate-100 shadow-2xl h-fit">
                                            <h3 className="text-xl font-black text-slate-900 mb-6">Velocity Timeline</h3>
                                            <div className="h-[250px]">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <AreaChart data={data?.trend || []}>
                                                        <defs>
                                                            <linearGradient id="colorReports" x1="0" y1="0" x2="0" y2="1">
                                                                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2} />
                                                                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                                                            </linearGradient>
                                                            <linearGradient id="colorResolved" x1="0" y1="0" x2="0" y2="1">
                                                                <stop offset="5%" stopColor="#10B981" stopOpacity={0.2} />
                                                                <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                                                            </linearGradient>
                                                        </defs>
                                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                                                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 700, fill: '#94A3B8' }} />
                                                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 700, fill: '#94A3B8' }} />
                                                        <Tooltip />
                                                        <Area type="monotone" dataKey="reports" stroke="#3B82F6" strokeWidth={3} fillOpacity={1} fill="url(#colorReports)" />
                                                        <Area type="monotone" dataKey="resolved" stroke="#10B981" strokeWidth={3} fillOpacity={1} fill="url(#colorResolved)" />
                                                    </AreaChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </section>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'audit' && (
                            <motion.div key="audit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40 overflow-hidden">
                                <div className="p-8 border-b bg-slate-50/50">
                                    <h3 className="text-xl font-black text-slate-900">System Audit Trail</h3>
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left">
                                        <thead className="bg-slate-50 text-[10px] uppercase font-black text-slate-400 tracking-[0.2em]">
                                            <tr>
                                                <th className="px-8 py-6">Timestamp</th>
                                                <th className="px-8 py-6">Action</th>
                                                <th className="px-8 py-6">Entity</th>
                                                <th className="px-8 py-6">Actor</th>
                                                <th className="px-8 py-6">Changes</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-50">
                                            {audits.map(log => (
                                                <tr key={log.id} className="hover:bg-slate-50/50 transition-colors">
                                                    <td className="px-8 py-6 text-xs font-bold text-slate-500">{new Date(log.created_at).toLocaleDateString()}</td>
                                                    <td className="px-8 py-6"><span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-[10px] font-black">{log.action}</span></td>
                                                    <td className="px-8 py-6 text-xs font-medium text-slate-600">#{log.entity_id.slice(0, 8)}</td>
                                                    <td className="px-8 py-6 text-xs font-black text-primary uppercase tracking-tight">#{log.actor_id.slice(0, 8)}</td>
                                                    <td className="px-8 py-6">
                                                        <div className="flex items-center gap-2 text-[10px] font-bold">
                                                            <span className="text-slate-400">{log.old_value || 'None'}</span>
                                                            <ChevronRight size={10} className="text-slate-300" />
                                                            <span className="text-emerald-600">{log.new_value}</span>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'config' && (
                            <motion.div key="config" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-12">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                                    {/* Organizations Card */}
                                    <div className="bg-white p-8 rounded-[3rem] border border-slate-100 shadow-xl">
                                        <div className="flex justify-between items-center mb-6">
                                            <div className="w-12 h-12 bg-blue-500 rounded-2xl flex items-center justify-center text-white shadow-lg">
                                                <Building2 size={24} />
                                            </div>
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{organizations.length} Active</span>
                                        </div>
                                        <h3 className="text-xl font-black text-slate-900 mb-6">Organizations</h3>
                                        <div className="space-y-3">
                                            {organizations.map(org => (
                                                <div key={org.id} className="p-4 bg-slate-50 rounded-2xl flex items-center justify-between group hover:bg-slate-100 transition-all cursor-default">
                                                    <span className="text-sm font-bold text-slate-600 tracking-tight">{org.name}</span>
                                                    <ArrowRight size={14} className="text-slate-300 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Category Registry */}
                                    <div className="bg-white p-8 rounded-[3rem] border border-slate-100 shadow-xl flex flex-col">
                                        <div className="flex justify-between items-center mb-6">
                                            <div className="w-12 h-12 bg-rose-500 rounded-2xl flex items-center justify-center text-white shadow-lg">
                                                <Layers size={24} />
                                            </div>
                                            <button 
                                                onClick={() => setShowAddCategory(true)}
                                                className="w-8 h-8 bg-slate-100 hover:bg-slate-200 rounded-full flex items-center justify-center text-slate-600 transition-all"
                                            >
                                                <UserPlus size={14} />
                                            </button>
                                        </div>
                                        <h3 className="text-xl font-black text-slate-900 mb-6">Category Registry</h3>
                                        <div className="space-y-3 flex-1 overflow-auto max-h-[300px] pr-2 scrollbar-hide">
                                            {categories.map(cat => (
                                                <div 
                                                    key={cat.id} 
                                                    onClick={() => setSelectedCategory(cat)}
                                                    className="p-4 bg-slate-50 rounded-2xl flex items-center justify-between group hover:bg-slate-100 transition-all cursor-pointer border border-transparent hover:border-slate-200"
                                                >
                                                    <span className="text-sm font-bold text-slate-600 tracking-tight">{cat.name}</span>
                                                    <div className="flex items-center gap-3">
                                                        <span className="text-[10px] font-black text-slate-400 uppercase">{cat.default_priority}</span>
                                                        <ArrowRight size={12} className="text-slate-300 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>


                                    {/* System Health */}
                                    <div className="bg-slate-900 p-8 rounded-[3rem] text-white shadow-2xl relative overflow-hidden">
                                        <div className="relative z-10 flex flex-col h-full">
                                            <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center shadow-lg mb-6">
                                                <Zap size={24} />
                                            </div>
                                            <h3 className="text-xl font-black mb-2">Platform Health</h3>
                                            <p className="text-slate-400 text-sm font-medium mb-8 leading-relaxed">Execute a full system diagnostic scan to verify API, Database, and Storage integrity.</p>

                                            <div className="mt-auto space-y-3">
                                                <button
                                                    onClick={() => setShowDiagnostics(true)}
                                                    className="w-full py-4 bg-white text-slate-900 rounded-2xl font-black text-xs uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-slate-100 transition-all"
                                                >
                                                    <Activity size={16} /> Run Diagnostics
                                                </button>
                                    <button 
                                        onClick={() => setShowOnboard(true)}
                                        className="w-full py-4 bg-white/10 text-white rounded-2xl font-black text-xs uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-white/20 transition-all border border-white/10"
                                    >
                                        <UserPlus size={16} /> Onboard Authority
                                    </button>
                                    <button 
                                        onClick={() => setShowOnboardWorker(true)}
                                        className="w-full py-4 bg-primary/20 text-white rounded-2xl font-black text-xs uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-primary/30 transition-all border border-primary/20"
                                    >
                                        <Users size={16} /> Onboard Worker
                                    </button>

                                            </div>
                                        </div>
                                        <div className="absolute -right-20 -top-20 w-64 h-64 bg-primary/20 rounded-full blur-[80px]"></div>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>

                <DiagnosticsModal isOpen={showDiagnostics} onClose={() => setShowDiagnostics(false)} />
                <OnboardModal isOpen={showOnboard} onClose={() => setShowOnboard(false)} organizations={organizations} />
                <OnboardWorkerModal isOpen={showOnboardWorker} onClose={() => setShowOnboardWorker(false)} organizations={organizations} onCreated={fetchAdminData} />
                <CategoryModal isOpen={showAddCategory} onClose={() => setShowAddCategory(false)} onCreated={fetchAdminData} />
                <CategoryDetailsModal isOpen={!!selectedCategory} onClose={() => setSelectedCategory(null)} category={selectedCategory} />
            </div>
        </div>
    )
}
