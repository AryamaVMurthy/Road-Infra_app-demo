import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import { 
    Settings, Shield, Globe, Activity, Database, LogOut, 
    TrendingUp, Users, AlertTriangle, CheckCircle, 
    ChevronRight, ArrowRight, Map as MapIcon, Plus, Trash2, Edit2, UserPlus, MapPin, XCircle, RefreshCw,
    Building2, PlusCircle, Tags, Menu, X
} from 'lucide-react'
import { authService } from '../../services/auth'
import adminService from '../../services/admin'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'
import { Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { useAutoRefresh } from '../../hooks/useAutoRefresh'
import MapboxDrawControl from '../../components/MapboxDrawControl'
import { InteractiveMap, Marker } from '../../components/InteractiveMap'
import { MAPBOX_TOKEN } from '../../config/map'

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
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024)
  const [data, setData] = useState(null)

  useEffect(() => {
    const handleResize = () => setIsDesktop(window.innerWidth >= 1024)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  const [audits, setAudits] = useState([])
  const [authorities, setAuthorities] = useState([])
  const [issueTypes, setIssueTypes] = useState([])
  const [showAddAuthority, setShowAddAuthority] = useState(false)
  const [showAddIssueType, setShowAddIssueType] = useState(false)
  const [editingIssueType, setEditingIssueType] = useState(null)
  
  const [newOrg, setNewOrg] = useState({ name: '', admin_email: '', zone_name: '' })
  const [newIT, setNewIT] = useState({ name: '', default_priority: 'P3', expected_sla_days: 7 })
  const [manualIssue, setManualIssue] = useState({ category_id: '', lat: null, lng: null, address: '', priority: '', org_id: '' })
  
  const [polygonPoints, setPolygonPoints] = useState([])
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [auditFilters, setAuditFilters] = useState({ action: '', startDate: '', endDate: '' })
  const [isEditingJurisdiction, setIsEditingJurisdiction] = useState(false)
  const [selectedOrgForEdit, setSelectedOrgForEdit] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, authoritiesRes, issueTypesRes] = await Promise.all([
        api.get('/analytics/stats'),
        adminService.getAuthorities(),
        adminService.getIssueTypes()
      ])
      
      setData(statsRes.data)
      setAuthorities(authoritiesRes.data)
      setIssueTypes(issueTypesRes.data)

      if (activeTab === 'logs') {
        const auditRes = await adminService.getAuditLogs(auditFilters)
        setAudits(auditRes.data)
      }

      setLastRefresh(new Date())
    } catch (err) {
      console.error('Failed to fetch admin data', err)
    }
  }, [activeTab, auditFilters])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useAutoRefresh(fetchData, { intervalMs: 30000, runOnMount: false })

  const stats = [
    { name: 'Total Issues', value: data?.summary?.reported || 0, color: 'bg-rose-500', icon: AlertTriangle },
    { name: 'Active Workers', value: data?.summary?.workers || 0, color: 'bg-blue-500', icon: Users },
    { name: 'Resolved', value: data?.summary?.resolved || 0, color: 'bg-emerald-500', icon: CheckCircle },
    { name: 'Compliance', value: data?.summary?.compliance || '0%', color: 'bg-purple-500', icon: Shield },
  ]

  const tabButton = (id, label, Icon) => (
    <button 
        onClick={() => setActiveTab(id)} 
        id={`btn-${id}`}
        className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", 
        activeTab === id ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}
    >
      <Icon size={20} /> <span className="text-sm">{label}</span>
    </button>
  )

  return (
    <div className="flex h-screen bg-[#F8FAFC] relative overflow-hidden">
      <AnimatePresence>
        {(isSidebarOpen || isDesktop) && (
          <motion.aside 
            initial={isDesktop ? false : { x: -320 }}
            animate={{ x: 0 }}
            exit={{ x: -320 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className={cn(
              "w-80 bg-slate-950 text-white flex flex-col p-8 fixed lg:relative z-[100] h-full shadow-2xl lg:shadow-none",
              !isSidebarOpen && !isDesktop && "hidden"
            )}
          >
            <div className="flex items-center justify-between mb-16">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-slate-950 shadow-xl shadow-white/10">
                        <Shield size={28} />
                    </div>
                    <div>
                        <h1 className="text-xl font-black tracking-tight leading-none">MARG IT Admin</h1>
                    </div>
                </div>
                <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden text-slate-500 hover:text-white">
                    <X size={24} />
                </button>
            </div>

            <nav className="flex-1 space-y-3">
                {tabButton('overview', 'Summary', Activity)}
                {tabButton('authorities', 'Authorities', Building2)}
                {tabButton('issue-types', 'Issue Types', Tags)}
                {tabButton('manual-issue', 'Manual Report', PlusCircle)}
                <button onClick={() => navigate('/analytics')} className="w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold text-slate-500 hover:text-white hover:bg-white/5 transition-all">
                  <Globe size={20} /> <span className="text-sm">Full Analytics</span>
                </button>
                {tabButton('logs', 'Audit Trails', Database)}
            </nav>

            <div className="mt-auto pt-8 border-t border-white/5">
              <button onClick={() => authService.logout()} className="w-full flex items-center gap-4 p-5 text-red-400 font-bold hover:bg-red-500/10 rounded-[1.5rem] transition-all">
                <LogOut size={20} /> <span className="text-sm">Exit System</span>
              </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-24 lg:h-28 px-6 lg:px-12 flex items-center justify-between bg-white/50 backdrop-blur-md">
            <div className="flex items-center gap-4">
                <button 
                    onClick={() => setIsSidebarOpen(true)}
                    className="lg:hidden w-10 h-10 bg-slate-900 text-white rounded-xl flex items-center justify-center shadow-lg"
                >
                    <Menu size={20} />
                </button>
                <h2 className="text-xl lg:text-3xl font-black text-slate-900 tracking-tight capitalize truncate">{activeTab.replace('-', ' ')}</h2>
            </div>
            <div className="flex items-center gap-4 pl-6 border-l border-slate-200">
                <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-xl text-xs font-bold text-slate-500 border border-slate-100">
                    <RefreshCw size={12} />
                    <span>Synced {lastRefresh.toLocaleTimeString()}</span>
                </div>
                <div className="text-right">
                    <p className="text-sm font-black text-slate-900">Chief Officer</p>
                    <p className="text-[10px] font-bold text-emerald-500 uppercase tracking-tighter">Verified Node</p>
                </div>
                <div className="w-14 h-14 bg-slate-900 rounded-[1.5rem] flex items-center justify-center text-white font-black shadow-lg">CO</div>
            </div>
        </header>

        <main className="flex-1 overflow-auto p-12 pt-4">
            <AnimatePresence mode="wait">
            {activeTab === 'overview' && (
                <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
                        {stats.map((s) => (
                            <AdminStat key={s.name} label={s.name} value={s.value} trend={s.trend} icon={s.icon} color={s.color} />
                        ))}
                    </div>
                </motion.div>
            )}

            {activeTab === 'authorities' && (
                <motion.div key="authorities" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-8">
                    <div className="flex justify-between items-center mb-8">
                        <h3 className="text-2xl font-black text-slate-900">Government Authorities</h3>
                        <button 
                            id="btn-register-authority"
                            onClick={() => setShowAddAuthority(true)}
                            className="bg-primary text-white px-6 py-3 rounded-2xl font-black shadow-xl shadow-primary/20 flex items-center gap-2"
                        >
                            <Plus size={20} /> Register New Authority
                        </button>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 bg-white rounded-[3rem] border border-slate-100 shadow-2xl overflow-hidden">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50 text-[10px] uppercase font-black text-slate-400 tracking-[0.2em]">
                                    <tr>
                                        <th className="px-8 py-6">Name</th>
                                        <th className="px-8 py-6">Jurisdiction</th>
                                        <th className="px-8 py-6">Admins/Workers</th>
                                        <th className="px-8 py-6 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-50">
                                    {authorities.map(org => (
                                        <tr key={org.org_id} className="hover:bg-slate-50 transition-colors">
                                            <td className="px-8 py-6 font-black text-slate-900">{org.name}</td>
                                            <td className="px-8 py-6 text-xs font-bold text-slate-500">{org.zone_name}</td>
                                            <td className="px-8 py-6 text-[10px] font-mono text-slate-400 uppercase tracking-tighter">
                                                {org.admin_count} Admins • {org.worker_count} Workers
                                            </td>
                                            <td className="px-8 py-6 text-right">
                                                <button 
                                                    onClick={() => {
                                                        setSelectedOrgForEdit(org);
                                                        setIsEditingJurisdiction(true);
                                                    }}
                                                    className="flex items-center gap-1.5 text-primary hover:underline font-black uppercase tracking-widest text-[9px]"
                                                >
                                                    <MapIcon size={12} />
                                                    Edit Jurisdiction
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="space-y-8">
                            {showAddAuthority && (
                                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                                    <div className="flex justify-between items-center mb-6">
                                        <h4 className="text-lg font-black text-slate-900">New Authority</h4>
                                        <button onClick={() => {setShowAddAuthority(false); setPolygonPoints([])}} className="text-slate-400"><XCircle size={20} /></button>
                                    </div>
                                    <div className="space-y-4">
                                        <input 
                                            data-testid="input-authority-name"
                                            placeholder="Authority Name" 
                                            className="w-full p-4 rounded-xl border-2 border-slate-50 focus:border-primary outline-none font-bold"
                                            value={newOrg.name}
                                            onChange={(e) => setNewOrg({...newOrg, name: e.target.value})}
                                        />
                                        <input 
                                            placeholder="Admin Email" 
                                            className="w-full p-4 rounded-xl border-2 border-slate-50 focus:border-primary outline-none font-bold"
                                            value={newOrg.admin_email}
                                            onChange={(e) => setNewOrg({...newOrg, admin_email: e.target.value})}
                                        />
                                        
                                        <div className="space-y-4">
                                                <div className="h-64 rounded-2xl overflow-hidden border-2 border-slate-100 relative">
                                                    <InteractiveMap
                                                        initialViewState={{ longitude: 77.5946, latitude: 12.9716, zoom: 11 }}
                                                        showGeocoder={true}
                                                        showLocate={true}
                                                    >

                                                    <MapboxDrawControl 
                                                        position="top-left"
                                                        displayControlsDefault={false}
                                                        controls={{
                                                            polygon: true,
                                                            trash: true
                                                        }}
                                                        defaultMode="draw_polygon"
                                                        onCreate={(e) => setPolygonPoints(e.features[0].geometry.coordinates[0])}
                                                        onUpdate={(e) => setPolygonPoints(e.features[0].geometry.coordinates[0])}
                                                    />
                                                </InteractiveMap>
                                                <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-md px-3 py-1.5 rounded-lg text-[10px] font-black text-slate-900 uppercase shadow-sm border border-slate-100">Draw Jurisdiction</div>
                                            </div>
                                            <button 
                                                id="btn-simulate-draw"
                                                className="fixed top-0 left-0 w-1 h-1 opacity-0 z-[5000]"
                                                onClick={() => {
                                                    const mockPoints = [[77.5, 12.9], [77.6, 12.9], [77.6, 13.0], [77.5, 13.0], [77.5, 12.9]];
                                                    setPolygonPoints(mockPoints);
                                                }}
                                            >
                                                Simulate Draw
                                            </button>
                                            
                                            {polygonPoints.length >= 3 ? (
                                                 <div className="p-4 bg-emerald-50 rounded-xl flex items-center gap-3">
                                                    <CheckCircle className="text-emerald-500" size={20} />
                                                    <span className="text-xs font-bold text-emerald-700 uppercase">Jurisdiction Defined</span>
                                                </div>
                                            ) : (
                                                <p className="text-[10px] text-slate-400 font-bold text-center italic">Minimum 3 points required on map</p>
                                            )}
                                        </div>

                                        <button 
                                            onClick={async () => {
                                                if (!newOrg.name || !newOrg.admin_email || polygonPoints.length < 3) return alert("Complete all steps");
                                                try {
                                                    await adminService.createAuthority({
                                                        name: newOrg.name,
                                                        admin_email: newOrg.admin_email,
                                                        jurisdiction_points: polygonPoints,
                                                        zone_name: newOrg.zone_name || undefined
                                                    });
                                                    setNewOrg({ name: '', admin_email: '', zone_name: '' });
                                                    setPolygonPoints([]);
                                                    setShowAddAuthority(false);
                                                    fetchData();
                                                } catch (err) { alert("Registration failed") }
                                            }}
                                            disabled={!newOrg.name || !newOrg.admin_email || polygonPoints.length < 3}
                                            className="w-full py-4 bg-primary text-white rounded-2xl font-black shadow-xl shadow-primary/20 disabled:opacity-50"
                                        >
                                            Register Authority
                                        </button>
                                    </div>
                                </motion.div>
                            )}
                        </div>
                    </div>
                </motion.div>
            )}

            {activeTab === 'issue-types' && (
                <motion.div key="issue-types" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-8">
                    <div className="flex justify-between items-center mb-8">
                        <h3 className="text-2xl font-black text-slate-900">System Issue Types</h3>
                        <button 
                            id="btn-create-type"
                            onClick={() => {setEditingIssueType(null); setNewIT({ name: '', default_priority: 'P3', expected_sla_days: 7 }); setShowAddIssueType(true)}}
                            className="bg-primary text-white px-6 py-3 rounded-2xl font-black shadow-xl shadow-primary/20 flex items-center gap-2"
                        >
                            <Plus size={20} /> Create Type
                        </button>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 bg-white rounded-[3rem] border border-slate-100 shadow-2xl overflow-hidden">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50 text-[10px] uppercase font-black text-slate-400 tracking-[0.2em]">
                                    <tr>
                                        <th className="px-8 py-6">Type</th>
                                        <th className="px-8 py-6">Priority</th>
                                        <th className="px-8 py-6">SLA (Days)</th>
                                        <th className="px-8 py-6">Status</th>
                                        <th className="px-8 py-6 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-50">
                                    {issueTypes.map(cat => (
                                        <tr key={cat.id} className="hover:bg-slate-50 transition-colors">
                                            <td className="px-8 py-6 font-black text-slate-900">{cat.name}</td>
                                            <td className="px-8 py-6">
                                                <span className={cn(
                                                    "px-3 py-1 rounded-full text-[10px] font-black",
                                                    cat.default_priority === 'P1' ? "bg-rose-50 text-rose-600" :
                                                    cat.default_priority === 'P2' ? "bg-amber-50 text-amber-600" : "bg-blue-50 text-blue-600"
                                                )}>
                                                    {cat.default_priority}
                                                </span>
                                            </td>
                                            <td className="px-8 py-6 text-xs font-bold text-slate-500">{cat.expected_sla_days} Days</td>
                                            <td className="px-8 py-6">
                                                <span className={cn(
                                                    "px-2 py-1 rounded-full text-[9px] font-black uppercase",
                                                    cat.is_active ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-400"
                                                )}>
                                                    {cat.is_active ? 'Active' : 'Disabled'}
                                                </span>
                                            </td>
                                            <td className="px-8 py-6 text-right">
                                                <div className="flex justify-end gap-2">
                                                    <button onClick={() => {setEditingIssueType(cat); setNewIT(cat); setShowAddIssueType(true)}} className="p-2 text-slate-400 hover:text-primary transition-colors btn-update-type"><Edit2 size={16} /></button>
                                                    <button 
                                                        onClick={async () => {
                                                            if (!window.confirm("Disable this category?")) return;
                                                            try {
                                                                await adminService.deleteIssueType(cat.id);
                                                                fetchData();
                                                            } catch (err) { alert("Action failed") }
                                                        }}
                                                        className="p-2 text-slate-400 hover:text-rose-500 transition-colors"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="space-y-8">
                            {showAddIssueType && (
                                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                                    <h4 className="text-lg font-black text-slate-900 mb-6">{editingIssueType ? 'Edit Type' : 'New Type'}</h4>
                                    <div className="space-y-4">
                                        <div>
                                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Type Name</label>
                                            <input 
                                                className="w-full p-4 mt-2 rounded-xl border-2 border-slate-50 focus:border-primary outline-none font-bold"
                                                value={newIT.name}
                                                onChange={(e) => setNewIT({...newIT, name: e.target.value})}
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Default Priority</label>
                                            <select 
                                                className="w-full p-4 mt-2 rounded-xl border-2 border-slate-50 focus:border-primary outline-none font-bold"
                                                value={newIT.default_priority}
                                                onChange={(e) => setNewIT({...newIT, default_priority: e.target.value})}
                                            >
                                                <option value="P1">P1 - Critical</option>
                                                <option value="P2">P2 - Urgent</option>
                                                <option value="P3">P3 - Standard</option>
                                                <option value="P4">P4 - Low</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">SLA Days</label>
                                            <input 
                                                type="number"
                                                className="w-full p-4 mt-2 rounded-xl border-2 border-slate-50 focus:border-primary outline-none font-bold"
                                                value={newIT.expected_sla_days}
                                                onChange={(e) => setNewIT({...newIT, expected_sla_days: parseInt(e.target.value)})}
                                            />
                                        </div>

                                        <div className="flex gap-3 pt-4">
                                            <button 
                                                onClick={() => {setShowAddIssueType(false); setEditingIssueType(null)}}
                                                className="flex-1 py-4 bg-slate-100 text-slate-500 rounded-2xl font-black"
                                            >
                                                Cancel
                                            </button>
                                            <button 
                                                id="btn-create-category-confirm"
                                                onClick={async () => {
                                                    try {
                                                        if (editingIssueType) {
                                                            await adminService.updateIssueType(editingIssueType.id, newIT);
                                                        } else {
                                                            await adminService.createIssueType(newIT);
                                                        }
                                                        setShowAddIssueType(false);
                                                        fetchData();
                                                    } catch (err) { alert("Save failed") }
                                                }}
                                                className="flex-[2] py-4 bg-primary text-white rounded-2xl font-black shadow-xl shadow-primary/20"
                                            >
                                                {editingIssueType ? 'Update' : 'Create'}
                                            </button>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </div>
                    </div>
                </motion.div>
            )}

            {activeTab === 'manual-issue' && (
                <motion.div key="manual-issue" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-4xl mx-auto space-y-10">
                    <div className="bg-white p-12 rounded-[3rem] border border-slate-100 shadow-2xl">
                         <div className="mb-12 text-center">
                            <h3 className="text-3xl font-black text-slate-900 mb-2">Manual Issue Registration</h3>
                            <p className="text-slate-500 font-bold uppercase text-[10px] tracking-[0.2em]">Administrative Override</p>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                             <div className="space-y-8">
                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">1. Set Location</label>
                                    <div className="h-80 rounded-3xl overflow-hidden border-4 border-slate-50 relative shadow-inner">
                                        <InteractiveMap
                                            initialViewState={{ longitude: 77.5946, latitude: 12.9716, zoom: 12 }}
                                            onLocationSelect={(latlng) => setManualIssue({...manualIssue, lat: latlng.lat, lng: latlng.lng})}
                                            onClick={(e) => setManualIssue({...manualIssue, lat: e.lngLat.lat, lng: e.lngLat.lng})}
                                        >
                                            {manualIssue.lat && <Marker longitude={manualIssue.lng} latitude={manualIssue.lat} />}
                                        </InteractiveMap>
                                    </div>
                                    {manualIssue.lat && (
                                        <div className="p-4 bg-blue-50 rounded-2xl flex items-center gap-3 border border-blue-100">
                                            <MapPin className="text-primary" size={18} />
                                            <span className="text-[10px] font-black text-primary uppercase tracking-tighter">
                                                Locked: {manualIssue.lat.toFixed(6)}, {manualIssue.lng.toFixed(6)}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="space-y-8">
                                <div className="space-y-6">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">2. Issue Details</label>
                                    <select 
                                        className="w-full p-5 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-primary focus:bg-white outline-none font-bold transition-all"
                                        value={manualIssue.category_id}
                                        onChange={(e) => setManualIssue({...manualIssue, category_id: e.target.value})}
                                    >
                                        <option value="">Select Type...</option>
                                        {issueTypes.filter(it => it.is_active).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                    
                                    <input 
                                        placeholder="Address (Optional)"
                                        className="w-full p-5 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-primary focus:bg-white outline-none font-bold transition-all"
                                        value={manualIssue.address}
                                        onChange={(e) => setManualIssue({...manualIssue, address: e.target.value})}
                                    />

                                    <select 
                                        className="w-full p-5 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-primary focus:bg-white outline-none font-bold transition-all"
                                        value={manualIssue.priority}
                                        onChange={(e) => setManualIssue({...manualIssue, priority: e.target.value})}
                                    >
                                        <option value="">Default Priority</option>
                                        <option value="P1">P1 - Critical</option>
                                        <option value="P2">P2 - Urgent</option>
                                        <option value="P3">P3 - Standard</option>
                                        <option value="P4">P4 - Low</option>
                                    </select>

                                    <button 
                                        onClick={async () => {
                                            if (!manualIssue.category_id || !manualIssue.lat) return alert("Required fields missing");
                                            try {
                                                await adminService.createManualIssue(manualIssue);
                                                alert("Issue created");
                                                setManualIssue({ category_id: '', lat: null, lng: null, address: '', priority: '', org_id: '' });
                                                fetchData();
                                            } catch (e) { alert("Creation failed") }
                                        }}
                                        className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black shadow-xl hover:scale-[1.02] active:scale-95 transition-all"
                                    >
                                        Create Manual Issue
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}

            {activeTab === 'logs' && (
                <motion.div key="logs" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-8">
                    <div className="bg-white p-8 rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40">
                        <div className="flex flex-wrap items-end gap-6">
                            <div className="flex-1 min-w-[200px] space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Action Type</label>
                                <select 
                                    className="w-full p-4 bg-slate-50 rounded-2xl border-none font-bold outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                                    value={auditFilters.action}
                                    onChange={(e) => setAuditFilters({...auditFilters, action: e.target.value})}
                                >
                                    <option value="">All Actions</option>
                                    <option value="STATUS_CHANGE">Status Change</option>
                                    <option value="ASSIGNMENT">Assignment</option>
                                    <option value="PRIORITY_CHANGE">Priority Change</option>
                                    <option value="INVITE_WORKER">Worker Invite</option>
                                    <option value="DEACTIVATE_WORKER">Worker Deactivation</option>
                                    <option value="APPROVE_ISSUE">Approve Issue</option>
                                    <option value="REJECT_ISSUE">Reject Issue</option>
                                    <option value="START_TASK">Start Task</option>
                                    <option value="RESOLVE_TASK">Resolve Task</option>
                                    <option value="CREATE_ZONE">Zone Creation</option>
                                    <option value="CREATE_ORG">Org Creation</option>
                                </select>
                            </div>
                            <div className="flex-1 min-w-[200px] space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Start Date</label>
                                <input 
                                    type="date"
                                    className="w-full p-4 bg-slate-50 rounded-2xl border-none font-bold outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                                    value={auditFilters.startDate}
                                    onChange={(e) => setAuditFilters({...auditFilters, startDate: e.target.value})}
                                />
                            </div>
                            <div className="flex-1 min-w-[200px] space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">End Date</label>
                                <input 
                                    type="date"
                                    className="w-full p-4 bg-slate-50 rounded-2xl border-none font-bold outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                                    value={auditFilters.endDate}
                                    onChange={(e) => setAuditFilters({...auditFilters, endDate: e.target.value})}
                                />
                            </div>
                            <button 
                                onClick={fetchData}
                                className="px-8 py-4 bg-slate-900 text-white rounded-2xl font-black shadow-xl hover:scale-[1.02] active:scale-95 transition-all"
                            >
                                Apply Filters
                            </button>
                            <button 
                                onClick={() => {
                                    setAuditFilters({ action: '', startDate: '', endDate: '' });
                                    fetchData();
                                }}
                                className="px-6 py-4 bg-slate-100 text-slate-500 rounded-2xl font-black hover:bg-slate-200 transition-all"
                            >
                                Reset
                            </button>
                        </div>
                    </div>

                    <div className="bg-white rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40 overflow-hidden">
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
                                            <td className="px-8 py-6 text-xs font-bold text-slate-500">{new Date(log.created_at).toLocaleString()}</td>
                                            <td className="px-8 py-6"><span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-[10px] font-black">{log.action}</span></td>
                                            <td className="px-8 py-6 text-xs font-medium text-slate-600">#{log.entity_id.slice(0,8)}</td>
                                            <td className="px-8 py-6 text-xs font-black text-primary uppercase tracking-tight">#{log.actor_id.slice(0,8)}</td>
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
                    </div>
                </motion.div>
            )}

            {isEditingJurisdiction && selectedOrgForEdit && (
                <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md z-[3000] flex items-center justify-center p-8">
                    <div className="bg-white w-full max-w-5xl h-[80vh] rounded-[3rem] overflow-hidden flex flex-col shadow-2xl">
                        <div className="p-8 flex justify-between items-center border-b">
                            <div>
                                <h3 className="text-2xl font-black text-slate-900">Edit Jurisdiction: {selectedOrgForEdit.name}</h3>
                                <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Draw or modify the boundary polygon on the map</p>
                            </div>
                            <button onClick={() => setIsEditingJurisdiction(false)} className="p-4 bg-slate-100 rounded-2xl text-slate-400 hover:text-slate-900 transition-all"><XCircle size={24} /></button>
                        </div>
                        <div className="flex-1 relative">
                            <InteractiveMap
                                initialViewState={{ longitude: 77.5946, latitude: 12.9716, zoom: 12 }}
                                showGeocoder={false}
                                showLocate={false}
                            >
                                <button 
                                    id="btn-simulate-edit-draw"
                                    className="fixed top-0 left-0 w-1 h-1 opacity-0 z-[5000]"
                                    onClick={() => {
                                        const mockPoints = [[77.6, 13.0], [77.7, 13.0], [77.7, 13.1], [77.6, 13.1], [77.6, 13.0]];
                                        setPolygonPoints(mockPoints);
                                    }}
                                >
                                    Simulate Edit Draw
                                </button>
                                <MapboxDrawControl 
                                    position="top-left"
                                    displayControlsDefault={false}
                                    controls={{
                                        polygon: true,
                                        trash: true
                                    }}
                                    defaultMode="draw_polygon"
                                    initialData={(() => {
                                        if (selectedOrgForEdit?.jurisdiction_points?.length >= 3) {
                                            return {
                                                type: 'FeatureCollection',
                                                features: [{
                                                    type: 'Feature',
                                                    properties: {},
                                                    geometry: {
                                                        type: 'Polygon',
                                                        coordinates: [selectedOrgForEdit.jurisdiction_points]
                                                    }
                                                }]
                                            };
                                        }
                                        return null;
                                    })()}
                                    onCreate={(e) => setPolygonPoints(e.features[0].geometry.coordinates[0])}
                                    onUpdate={(e) => setPolygonPoints(e.features[0].geometry.coordinates[0])}
                                />
                            </InteractiveMap>
                        </div>
                        <div className="p-8 bg-slate-50 border-t flex justify-end gap-4">
                            <button onClick={() => setIsEditingJurisdiction(false)} className="px-8 py-4 bg-white border border-slate-200 text-slate-500 rounded-2xl font-black transition-all hover:bg-slate-100">Cancel</button>
                            <button 
                                onClick={async () => {
                                    if (polygonPoints.length < 3) return alert("Please draw a valid polygon");
                                    try {
                                        await adminService.updateAuthority(selectedOrgForEdit.org_id, { 
                                            jurisdiction_points: polygonPoints 
                                        });
                                        alert("Jurisdiction updated successfully!");
                                        setIsEditingJurisdiction(false);
                                        fetchData();
                                    } catch (err) { alert("Failed to update jurisdiction") }
                                }}
                                className="px-10 py-4 bg-primary text-white rounded-2xl font-black shadow-xl shadow-primary/20 transition-all hover:scale-[1.02] active:scale-95"
                            >
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            )}
            </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
