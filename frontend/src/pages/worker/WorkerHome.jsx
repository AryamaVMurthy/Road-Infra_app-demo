import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import { 
    Briefcase, Clock, LogOut, Loader2, Activity, Map as MapIcon, Globe
} from 'lucide-react'
import { authService } from '../../services/auth'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/utils'
import { useNavigate } from 'react-router-dom'
import Map from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { MapboxHeatmap } from '../../components/MapboxHeatmap'
import { MapboxLocateControl } from '../../components/MapboxLocateControl'
import { MapboxGeocoderControl } from '../../components/MapboxGeocoder'
import { useGeolocation, DEFAULT_CENTER } from '../../hooks/useGeolocation'
import { useWorkerTasks } from '../../hooks/useWorkerTasks'
import { useAutoRefresh } from '../../hooks/useAutoRefresh'

import { TaskCard } from '../../features/worker/components/TaskList/TaskCard'
import { AcceptTaskModal } from '../../features/worker/components/Modals/AcceptTaskModal'
import { ResolveTaskModal } from '../../features/worker/components/Modals/ResolveTaskModal'
import { Toast } from '../../features/common/components/Toast'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example';

export default function WorkerHome() {
  const [activeTab, setActiveTab] = useState('tasks') 
  const [heatmapData, setHeatmapData] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [resolveTask, setResolveTask] = useState(null)
  const [eta, setEta] = useState('')
  const [resolveEtaDate, setResolveEtaDate] = useState('')
  const [resolvePhoto, setResolvePhoto] = useState(null)
  const [isResolving, setIsResolving] = useState(false)
  const [toast, setToast] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const navigate = useNavigate()

  const { position: geoPosition } = useGeolocation()
  const userLocation = geoPosition ? [geoPosition.lat, geoPosition.lng] : [DEFAULT_CENTER.lat, DEFAULT_CENTER.lng]

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, [])

  const handleTaskFetchError = useCallback((message) => {
    showToast(message, 'error')
  }, [showToast])

  const { tasks, loading, fetchTasks } = useWorkerTasks(handleTaskFetchError)

  const fetchHeatmap = useCallback(async () => {
    try {
      const response = await api.get('/analytics/heatmap')
      setHeatmapData(response.data)
    } catch {
      showToast('Failed to load heatmap data.', 'error')
    }
  }, [showToast])

  useEffect(() => {
    fetchHeatmap()
    setLastRefresh(new Date())
  }, [fetchHeatmap])

  const refreshDashboardData = useCallback(() => {
    fetchTasks({ showLoader: false })
    fetchHeatmap()
    setLastRefresh(new Date())
  }, [fetchTasks, fetchHeatmap])

  useAutoRefresh(refreshDashboardData, { intervalMs: 30000, runOnMount: false })

  const handleAccept = async (taskId) => {
    try {
        const etaDate = new Date(eta).toISOString();
        await api.post(`/worker/tasks/${taskId}/accept?eta_date=${encodeURIComponent(etaDate)}`);
        showToast('Task successfully accepted.', 'success');
        fetchTasks();
        setSelectedTask(null);
        setEta('');
    } catch (err) { 
      showToast('Failed to synchronize status.', 'error'); 
    }
  };

  const handleResolveSubmit = async () => {
    if (!resolvePhoto || !resolveTask) return;
    
    setIsResolving(true);

    try {
      const formData = new FormData();
      formData.append('photo', resolvePhoto);
      await api.post(`/worker/tasks/${resolveTask.id}/resolve`, formData);
      showToast('Task resolved successfully!', 'success');
      fetchTasks();
      setResolveTask(null);
      setResolvePhoto(null);
      setResolveEtaDate('');
    } catch (err) {
      showToast('Failed to resolve task.', 'error');
    }
    setIsResolving(false);
  };


  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <header className="px-8 py-10 bg-white/80 backdrop-blur-xl border-b border-slate-100 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <div className="flex items-center gap-5">
           <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center text-white shadow-2xl shadow-primary/30">
              <Briefcase size={28} />
           </div>
           <div>
              <h1 className="text-xl font-black text-slate-900 leading-none tracking-tight">MARG</h1>
              <div className="flex items-center gap-2 mt-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                <p className="text-[10px] font-black text-slate-400 tracking-widest uppercase">
                  Agent: Online
                </p>
              </div>
           </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-xl text-xs font-bold text-slate-500 border border-slate-100">
            <Activity size={12} />
            <span>Synced {lastRefresh.toLocaleTimeString()}</span>
          </div>
          <button onClick={() => authService.logout()} className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all border border-slate-100 shadow-sm">
            <LogOut size={20} />
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-8 pb-32 max-w-3xl mx-auto w-full">
        <AnimatePresence mode="wait">
          {activeTab === 'tasks' ? (
            <motion.div key="tasks" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-8">
                <div className="flex items-center justify-between px-2 mb-2">
                    <div className="space-y-1">
                        <h2 className="text-3xl font-black text-slate-900">Assigned Tasks</h2>
                    </div>
                    <div className="text-right">
                        <p className="text-2xl font-black text-primary">{tasks.length}</p>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">Pending</p>
                    </div>
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <Loader2 className="animate-spin text-primary" size={32} />
                        <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Refreshing task pool...</p>
                    </div>
                ) : tasks.length === 0 ? (
                    <div className="bg-white rounded-[3rem] p-12 text-center border border-slate-100 shadow-xl">
                        <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6 text-slate-200">
                            <Activity size={32} />
                        </div>
                        <h3 className="text-xl font-black text-slate-900 mb-2">Clear Schedule</h3>
                        <p className="text-slate-400 font-bold text-sm">No infrastructure reports require your attention.</p>
                    </div>
                ) : (
                    tasks.map((task, idx) => (
                        <TaskCard 
                          key={task.id} 
                          task={task} 
                          idx={idx} 
                          onSelect={setSelectedTask}
                          onResolve={setResolveTask}
                        />
                    ))
                )}
            </motion.div>
          ) : activeTab === 'map' ? (
            <motion.div key="map" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="h-[70vh] space-y-8">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-3xl font-black text-slate-900">Workzone Map</h2>
                </div>
                <div className="h-full w-full rounded-[3rem] overflow-hidden border-8 border-white shadow-2xl relative">
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
                        <MapboxHeatmap points={heatmapData} />
                        <MapboxLocateControl />
                        <MapboxGeocoderControl mapboxAccessToken={MAPBOX_TOKEN} />
                    </Map>
                </div>
            </motion.div>
          ) : (
            <motion.div key="history" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                <div className="flex items-center justify-between px-2 mb-2">
                    <div className="space-y-1">
                        <h2 className="text-3xl font-black text-slate-900">Service History</h2>
                        <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Completed Tasks</p>
                    </div>
                    <div className="text-right">
                        <p className="text-2xl font-black text-emerald-600">{tasks.filter(t => t.status === 'RESOLVED' || t.status === 'CLOSED').length}</p>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">Resolved</p>
                    </div>
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <Loader2 className="animate-spin text-primary" size={32} />
                        <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Loading history...</p>
                    </div>
                ) : tasks.filter(t => t.status === 'RESOLVED' || t.status === 'CLOSED').length === 0 ? (
                    <div className="bg-white rounded-[3rem] p-12 text-center border border-slate-100 shadow-xl">
                        <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6 text-slate-200">
                            <Clock size={32} />
                        </div>
                        <h3 className="text-xl font-black text-slate-900 mb-2">No History Yet</h3>
                        <p className="text-slate-400 font-bold text-sm">Completed resolutions will appear here after administrative approval.</p>
                    </div>
                ) : (
                    tasks.filter(t => t.status === 'RESOLVED' || t.status === 'CLOSED').map((task, idx) => (
                        <motion.div 
                            key={task.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            className="bg-white rounded-[2rem] p-6 border border-slate-100 shadow-lg"
                        >
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${task.status === 'CLOSED' ? 'bg-emerald-500' : 'bg-amber-500'}`}></div>
                                    <span className="text-xs font-black text-slate-400 uppercase tracking-widest">{task.status}</span>
                                </div>
                                <span className="text-xs font-bold text-slate-400">
                                    {task.resolved_at ? new Date(task.resolved_at).toLocaleDateString() : ''}
                                </span>
                            </div>
                            <h4 className="text-lg font-black text-slate-900 mb-2">{task.category_name}</h4>
                            <p className="text-sm text-slate-500 mb-3">{task.address || 'Location not specified'}</p>
                            <div className="flex items-center gap-4 text-xs text-slate-400">
                                <span className={`px-2 py-1 rounded-lg font-bold ${
                                    task.priority === 'P1' ? 'bg-red-50 text-red-600' :
                                    task.priority === 'P2' ? 'bg-amber-50 text-amber-600' :
                                    'bg-slate-50 text-slate-600'
                                }`}>
                                    {task.priority}
                                </span>
                                {task.eta_date && (
                                    <span className="flex items-center gap-1">
                                        <Clock size={12} />
                                        ETA: {new Date(task.eta_date).toLocaleDateString()}
                                    </span>
                                )}
                            </div>
                        </motion.div>
                    ))
                )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <nav className="h-28 bg-white/80 backdrop-blur-2xl border-t border-slate-100 fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around px-10 shadow-[0_-10px_30px_rgba(0,0,0,0.02)]">
        <button onClick={() => setActiveTab('tasks')} className={cn("flex flex-col items-center gap-1.5 transition-all", activeTab === 'tasks' ? "text-primary scale-110" : "text-slate-300 hover:text-slate-500")}>
          <Briefcase size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">Tasks</span>
        </button>

        <button onClick={() => setActiveTab('map')} className={cn("flex flex-col items-center gap-1.5 transition-all", activeTab === 'map' ? "text-primary scale-110" : "text-slate-300 hover:text-slate-500")}>
          <MapIcon size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">Area Map</span>
        </button>

        <button onClick={() => navigate('/analytics')} className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-primary transition-all">
          <Globe size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">City Health</span>
        </button>
        
        <button onClick={() => setActiveTab('history')} className={cn("flex flex-col items-center gap-1.5 transition-all", activeTab === 'history' ? "text-primary scale-110" : "text-slate-300 hover:text-slate-500")}>
          <Clock size={28} />
          <span className="text-[10px] font-black uppercase tracking-tighter">History</span>
        </button>
      </nav>

      <AcceptTaskModal 
        task={selectedTask}
        eta={eta}
        onEtaChange={setEta}
        onConfirm={() => handleAccept(selectedTask.id)}
        onCancel={() => setSelectedTask(null)}
      />

      <ResolveTaskModal 
        task={resolveTask}
        photo={resolvePhoto}
        onPhotoChange={setResolvePhoto}
        onSubmit={handleResolveSubmit}
        onCancel={() => { setResolveTask(null); setResolvePhoto(null); setResolveEtaDate(''); }}
        isResolving={isResolving}
        etaDate={resolveEtaDate}
        onEtaDateChange={setResolveEtaDate}
      />

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  )
}
