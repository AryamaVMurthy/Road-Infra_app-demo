import React, { useState, useEffect } from 'react'
import api from '../../services/api'
import { MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet.heat'
import { 
    Settings, Shield, Globe, Activity, Database, LogOut, 
    TrendingUp, Users, AlertTriangle, CheckCircle, MapPin, 
    ChevronRight, Download, Filter, Clock, ArrowRight
} from 'lucide-react'
import { authService } from '../../services/auth'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { 
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
    ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area 
} from 'recharts'
import { HeatmapLayer } from '../../components/HeatmapLayer'
import { LocateControl } from '../../components/LocateControl'
import { SearchField } from '../../components/SearchField'
import { useNavigate } from 'react-router-dom'

const MAP_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

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
  const [activeTab, setActiveTab] = useState('overview')
  const [data, setData] = useState(null)
  const [audits, setAudits] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchAdminData()
  }, [activeTab])

  const fetchAdminData = () => {
    const promises = [
      api.get('/admin/issues'),
      api.get('/admin/workers'),
      api.get('/analytics/stats')
    ]
    
    if (activeTab === 'logs') {
        promises.push(api.get('/analytics/audit-all').catch(() => ({data: []})))
    } else {
        promises.push(Promise.resolve({data: []}))
    }

    Promise.all(promises).then(([issuesRes, workersRes, statsRes, auditRes]) => {
      setData(statsRes.data)
      setAudits(auditRes.data)
    }).catch(() => {
    }).finally(() => setLoading(false))
  }

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
             <h1 className="text-xl font-black tracking-tight leading-none">SysAdmin</h1>
             <p className="text-[10px] font-bold text-slate-500 tracking-widest uppercase mt-1">Platform Engine</p>
           </div>
        </div>

        <nav className="flex-1 space-y-3">
           <button onClick={() => setActiveTab('overview')} className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", activeTab === 'overview' ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}>
             <Activity size={20} /> <span className="text-sm">Summary</span>
           </button>
           <button onClick={() => navigate('/analytics')} className="w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold text-slate-500 hover:text-white hover:bg-white/5 transition-all">
             <Globe size={20} /> <span className="text-sm">Full Analytics</span>
           </button>
           <button onClick={() => setActiveTab('config')} className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", activeTab === 'config' ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}>
             <Settings size={20} /> <span className="text-sm">System Config</span>
           </button>
           <button onClick={() => setActiveTab('logs')} className={cn("w-full flex items-center gap-4 p-5 rounded-[1.5rem] font-bold transition-all", activeTab === 'logs' ? "bg-white text-slate-950 shadow-xl" : "text-slate-500 hover:text-white hover:bg-white/5")}>
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
                <p className="text-sm font-medium text-slate-400">Monitoring Municipal Operations across Hyderabad.</p>
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
            {activeTab === 'overview' && (
                <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
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
                                            {data?.category_split.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={['#3B82F6', '#EF4444', '#F59E0B', '#10B981'][index % 4]} />
                                            ))}
                                        </Pie>
                                        <Tooltip />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="space-y-4 mt-8">
                                {data?.category_split.map((d, i) => (
                                    <div key={d.name} className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: ['#3B82F6', '#EF4444', '#F59E0B', '#10B981'][i % 4]}}></div>
                                            <span className="text-sm font-bold text-slate-600 uppercase tracking-tighter">{d.name}</span>
                                        </div>
                                        <span className="text-sm font-black text-slate-900">{d.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <motion.div 
                            whileHover={{ scale: 1.01 }}
                            onClick={() => navigate('/analytics')}
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

            {activeTab === 'logs' && (
                <motion.div key="logs" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40 overflow-hidden">
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
                </motion.div>
            )}
            </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
