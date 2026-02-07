import { useState, useEffect } from 'react'
import api from '../services/api'
import { 
    XAxis, YAxis, CartesianGrid, Tooltip, 
    ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area 
} from 'recharts'
import { 
    Globe, TrendingUp, AlertTriangle, CheckCircle2, CheckCircle,
    ArrowLeft, Activity as ActivityIcon, Users,
    ShieldCheck, Zap, Clock
} from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '../utils/utils'
import { useNavigate } from 'react-router-dom'
import Map, { Marker, Popup } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { MapboxHeatmap } from '../components/MapboxHeatmap'
import { MapboxLocateControl } from '../components/MapboxLocateControl'
import { MapboxGeocoderControl } from '../components/MapboxGeocoder'
import { useGeolocation, DEFAULT_CENTER } from '../hooks/useGeolocation'


const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example';

const StatBox = ({ label, value, trend, icon: Icon, colorClass }) => (
    <motion.div 
        whileHover={{ y: -5 }}
        className="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-[0_20px_50px_-12px_rgba(0,0,0,0.05)] relative overflow-hidden group"
    >
        <div className="flex justify-between items-start mb-6">
            <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center text-white shadow-lg", colorClass)}>
                <Icon size={24} />
            </div>
            {trend && (
                <div className="flex items-center gap-1 text-emerald-500 font-black text-xs bg-emerald-50 px-3 py-1 rounded-full border border-emerald-100">
                    <TrendingUp size={12} /> {trend}
                </div>
            )}
        </div>
        <p className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-1.5">{label}</p>
        <p className="text-4xl font-black text-slate-900">{value}</p>
        <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-slate-50 rounded-full group-hover:scale-150 transition-transform duration-700 opacity-30"></div>
    </motion.div>
)

export default function AnalyticsDashboard() {
  const [data, setData] = useState(null)
  const [heatmapData, setHeatmapData] = useState([])
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('heatmap')
  const navigate = useNavigate()

  const { position: geoPosition } = useGeolocation()
  const userLocation = geoPosition ? [geoPosition.lat, geoPosition.lng] : [DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    setLoading(true)
    try {
      const [statsRes, heatRes, issuesRes] = await Promise.all([
        api.get('/analytics/stats'),
        api.get('/analytics/heatmap'),
        api.get('/analytics/issues-public')
      ])
      setData(statsRes.data)
      setHeatmapData(heatRes.data)
      setIssues(issuesRes.data)
    } catch (err) {
      console.error("Failed to fetch analytics", err)
    }
    setLoading(false)
  }

  if (loading) {
      return (
          <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-6">
              <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-primary animate-spin"></div>
              <p className="text-sm font-black text-slate-400 uppercase tracking-widest">Compiling Intelligence...</p>
          </div>
      )
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans">
      <header className="px-10 py-8 bg-white/80 backdrop-blur-xl border-b border-slate-100 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <div className="flex items-center gap-6">
            <button onClick={() => navigate(-1)} className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-400 hover:text-primary hover:bg-white hover:shadow-md transition-all border border-slate-100">
                <ArrowLeft size={20} />
            </button>
            <div>
                <h1 className="text-2xl font-black tracking-tight text-slate-900">City Health Intelligence</h1>
            </div>
        </div>
        <div className="flex items-center gap-4">
            <div className="px-5 py-2.5 bg-slate-50 rounded-2xl border border-slate-100 flex items-center gap-3">
                <Clock size={16} className="text-slate-400" />
                <span className="text-sm font-bold text-slate-600">Last Sync: Just Now</span>
            </div>
            <button onClick={fetchAnalytics} className="p-3 bg-primary text-white rounded-2xl shadow-lg shadow-primary/20 hover:bg-blue-700 transition-all active:scale-95">
                <ActivityIcon size={20} />
            </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full p-10 space-y-12">
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <StatBox label="Total Reports" value={data?.summary.reported || 0} icon={AlertTriangle} colorClass="bg-rose-500" />
            <StatBox label="Resolved Tickets" value={data?.summary.resolved || 0} icon={CheckCircle2} colorClass="bg-emerald-500" />
            <StatBox label="Field Force" value={data?.summary.workers || 0} icon={Users} colorClass="bg-blue-500" />
            <StatBox label="SLA Compliance" value={data?.summary.compliance || '0%'} icon={ShieldCheck} colorClass="bg-purple-500" />
        </section>

        {/* Central Visualization Hub */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            <motion.div 
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="lg:col-span-2 bg-white rounded-[3.5rem] p-10 border border-slate-100 shadow-2xl relative overflow-hidden"
            >
                <div className="flex items-center justify-between mb-8 px-2">
                    <div className="space-y-1">
                        <h3 className="text-2xl font-black text-slate-900">Geospatial Insights</h3>
                        <p className="text-sm font-bold text-slate-400 uppercase tracking-tighter">Live Municipal Analysis</p>
                    </div>
                    <div className="flex bg-slate-100 p-1 rounded-2xl border shadow-inner">
                        <button 
                            onClick={() => setViewMode('heatmap')}
                            className={cn("px-4 py-2 rounded-xl text-[10px] font-black uppercase transition-all", viewMode === 'heatmap' ? "bg-primary text-white shadow-md" : "text-slate-500 hover:text-slate-900")}
                        >
                            Heatmap
                        </button>
                        <button 
                            onClick={() => setViewMode('markers')}
                            className={cn("px-4 py-2 rounded-xl text-[10px] font-black uppercase transition-all", viewMode === 'markers' ? "bg-primary text-white shadow-md" : "text-slate-500 hover:text-slate-900")}
                        >
                            Live Markers
                        </button>
                    </div>
                </div>
                <div className="h-[500px] w-full rounded-[2.5rem] overflow-hidden border-8 border-slate-50 shadow-inner relative">
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
                        {viewMode === 'heatmap' ? (
                            <MapboxHeatmap points={heatmapData} />
                        ) : (
                            issues.map(issue => (
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
                </div>
            </motion.div>

            <div className="flex flex-col gap-12">
                <motion.div 
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="bg-white p-10 rounded-[3rem] border border-slate-100 shadow-2xl"
                >
                    <h3 className="text-xl font-black text-slate-900 mb-2">Category Distribution</h3>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-10">Issue Proportionality</p>
                    <div className="h-[260px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie 
                                    data={data?.category_split || []} 
                                    innerRadius={70} 
                                    outerRadius={95} 
                                    paddingAngle={5} 
                                    dataKey="value"
                                    stroke="none"
                                >
                                    {(data?.category_split || []).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={['#3B82F6', '#EF4444', '#F59E0B', '#10B981'][index % 4]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{borderRadius: '20px', border: 'none', boxShadow: '0 20px 40px rgba(0,0,0,0.1)'}} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-8">
                        {(data?.category_split || []).map((d, i) => (
                            <div key={d.name} className="flex items-center gap-3">
                                <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: ['#3B82F6', '#EF4444', '#F59E0B', '#10B981'][i % 4]}}></div>
                                <span className="text-xs font-black text-slate-600 truncate uppercase tracking-tighter">{d.name}</span>
                            </div>
                        ))}
                    </div>
                </motion.div>

                <motion.div 
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                    className="bg-slate-900 rounded-[3rem] p-10 text-white relative overflow-hidden shadow-2xl shadow-slate-900/40"
                >
                    <div className="relative z-10 space-y-6">
                        <div className="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center text-primary border border-white/5 shadow-inner">
                            <Zap size={24} />
                        </div>
                        <h3 className="text-2xl font-black tracking-tight">System Status</h3>
                        <div className="space-y-4">
                            <div className="flex justify-between items-end">
                                <p className="text-xs font-bold text-slate-400">ACTIVE ISSUES</p>
                                <p className="text-xl font-black text-emerald-400">{(data?.summary.reported || 0) - (data?.summary.resolved || 0)}</p>
                            </div>
                            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                <div className="h-full bg-primary" style={{width: `${data?.summary.reported > 0 ? ((data?.summary.resolved || 0) / data?.summary.reported * 100) : 0}%`}}></div>
                            </div>
                            <p className="text-[10px] font-medium text-slate-500 leading-relaxed">
                                Resolution progress based on actual data.
                            </p>
                        </div>
                    </div>
                    <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-primary/20 rounded-full blur-3xl"></div>
                </motion.div>
            </div>
        </div>

        {/* Velocity Timeline Graph */}
        <section className="bg-white p-12 rounded-[4rem] border border-slate-100 shadow-2xl">
            <div className="flex items-center justify-between mb-12 px-2">
                <div className="space-y-1">
                    <h3 className="text-2xl font-black text-slate-900">Incident Trends</h3>
                    <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Temporal Growth Analysis</p>
                </div>
            </div>
            <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data?.trend || []}>
                        <defs>
                            <linearGradient id="colorReports" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2}/>
                                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id="colorResolved" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10B981" stopOpacity={0.2}/>
                                <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 12, fontWeight: 700, fill: '#94A3B8'}} dy={10} />
                        <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12, fontWeight: 700, fill: '#94A3B8'}} />
                        <Tooltip contentStyle={{borderRadius: '24px', border: 'none', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.15)'}} />
                        <Area type="monotone" dataKey="reports" stroke="#3B82F6" strokeWidth={4} fillOpacity={1} fill="url(#colorReports)" />
                        <Area type="monotone" dataKey="resolved" stroke="#10B981" strokeWidth={4} fillOpacity={1} fill="url(#colorResolved)" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </section>
        
        <section className="bg-primary p-12 rounded-[4rem] text-white relative overflow-hidden shadow-2xl shadow-primary/30 border border-white/10">
            <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                <div>
                    <h3 className="text-4xl font-black mb-6 tracking-tight">System Transparency</h3>
                    <p className="text-xl text-blue-100 font-medium leading-relaxed mb-10 max-w-xl">
                        This control plane provides real-time visibility into city operations. Every data point is cross-verified by GPS and binary image analysis to ensure absolute governance integrity.
                    </p>
                </div>
                <div className="grid grid-cols-2 gap-6">
                    {[
                        { label: 'Total Reports', val: data?.summary.reported || 0, icon: Zap },
                        { label: 'Resolved', val: data?.summary.resolved || 0, icon: CheckCircle },
                        { label: 'Workers', val: data?.summary.workers || 0, icon: Users },
                        { label: 'Region', val: 'Citywide', icon: Globe },
                    ].map(item => (
                        <div key={item.label} className="p-8 bg-white/5 rounded-3xl border border-white/5 backdrop-blur-sm shadow-inner group hover:bg-white/10 transition-colors">
                            <item.icon size={24} className="text-blue-300 mb-4 group-hover:scale-110 transition-transform" />
                            <p className="text-3xl font-black mb-1">{item.val}</p>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{item.label}</p>
                        </div>
                    ))}
                </div>
            </div>
            <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-white/5 rounded-full blur-[140px] -mr-40 -mt-40"></div>
            <div className="absolute bottom-0 left-0 w-80 h-80 bg-blue-400/10 rounded-full blur-[100px] -ml-20 -mb-20"></div>
        </section>
      </main>

      <footer className="py-12 border-t border-slate-100 text-center">
      </footer>
    </div>
  )
}
